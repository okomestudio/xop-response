# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
# Copyright (c) 2017 Taro Sato
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import absolute_import
import logging
import re
from contextlib import contextmanager
from email.parser import HeaderParser
from itertools import chain
from StringIO import StringIO

from .exceptions import ParsingError


log = logging.getLogger(__name__)


NL = b'\r\n'
#: byte: The new line used to delimit lines


def _generic_line_generator(stream, strip_newline=True):
    """Generator of lines from stream.

    Args:
        stream (`file`-like object): A stream from which lines are
            generated.

        strip_newline (bool): `True` if strip newline from the
            generated line. `False` to leave it unstripped.

    Returns:
        str: Each call generates a line from stream.

    """
    for line in stream:
        if strip_newline:
            # NOTE (ts): Is this rstripping necessary?
            if line.endswith(NL):
                line = line[:-2]
            elif line.endswith('\n'):
                line = line[:-1]
        yield line


re_split_content_type = re.compile(r'(;|' + NL + ')')


def parse_content_type(text):
    """Parse out parameters from `content-type`.

    Args:
        text (str): The `content-type` text.


    Returns:
        dict: The parameters parsed out from `content-type`.

    """
    items = re_split_content_type.split(text)
    d = {'mime-type': items.pop(0).lower()}
    for item in items:
        item = item.strip()
        try:
            idx = item.index('=')
            k = item[:idx]
            v = item[idx + 1:]
        except Exception:
            continue
        d[k] = v.strip('"')
    return d


class Part(dict):
    """A wrapper for a single message."""


class StreamContent(object):
    """The file-like interface for reading stream content.

    Args:
        streamer (:class:`MIMEStreamer`): The streamer object
            representing the MIME content.

    """

    def __init__(self, streamer):
        assert isinstance(streamer, MIMEStreamer)
        self._streamer = streamer
        self._buff = ''
        self._pos = 0
        self._eof_seen = False

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def __iter__(self):
        return self

    def next(self):
        if self._eof_seen:
            raise StopIteration
        if self._pos >= len(self._buff) - 1:
            l = next(self._streamer._ilines)
            log.debug('%r read: %s%s',
                      self, l[:50], '...' if len(l) > 50 else '')
            if self._streamer._is_boundary(l):
                log.debug('%r detected boundary', self)
                self._streamer._ilines = chain([l], self._streamer._ilines)
                self._eof_seen = True
                raise StopIteration
            self._buff = l + NL
            self._pos = -1
        self._pos += 1
        return self._buff[self._pos]

    def read(self, n=-1):
        assert n != 0
        buff = ''
        if n > 0:
            for i in xrange(n):
                try:
                    c = next(self)
                except StopIteration:
                    break
                buff += c
        else:
            while 1:
                try:
                    c = next(self)
                except StopIteration:
                    break
                buff += c
        return buff


class MIMEStreamer(object):
    """The generic MIME content streamer.

    Args:
        stream (`file`): The `file`-like object that reads from a
            string buffer of content in the MIME format.
        boundary (`str`, optional): The MIME part boundary text.
        line_generator (generator, optional): A generator which takes
            in `stream` and generates lines.

    """

    def __init__(self, stream, boundary=None, line_generator=None):
        self._ilines = (line_generator or _generic_line_generator)(stream)
        self._boundary = boundary or None

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def _is_boundary(self, line):
        return self._boundary and line.startswith('--' + self._boundary)

    def iterparts(self):
        while 1:
            with self.get_next_part() as part:
                if part is None:
                    break
                else:
                    yield part

    @contextmanager
    def get_next_part(self):
        """Get the next part. Use this with the context manager (i.e., `with`
        statement).

        """
        # Assume the cursor is at the first char of headers of a part
        part = Part({'content': None, 'headers': None})
        headers = []

        while 1:
            try:
                line = next(self._ilines)
            except StopIteration:
                raise ParsingError('Error parsing malformed content')

            log.debug('%r read: %s%s',
                      self, line[:76], '...' if len(line) > 76 else '')

            if self._is_boundary(line):
                # A boundary followed by an empty line indicates the
                # end of response content
                is_eof = False
                try:
                    next_line = next(self._ilines)
                except StopIteration:
                    is_eof = True
                else:
                    if next_line.strip() == '':
                        is_eof = True
                if is_eof:
                    log.debug('Content ends')
                    part = None
                    break

                self._ilines = chain([next_line], self._ilines)
                continue

            # Keep reading till the boundary is found and a new part
            # is initialized
            if part is None:
                continue

            if part['headers'] is None:
                rstripped_line = line.rstrip()
                if rstripped_line == '':
                    # This empty line separates headers and content in
                    # the current part
                    log.debug('End headers %r', headers)
                    headers = HeaderParser().parsestr(NL.join(headers))
                    part['headers'] = headers

                    if not self._boundary and 'content-type' in headers:
                        # Try looking for boundary info in this header
                        pars = parse_content_type(headers['content-type'])
                        if pars['mime-type'].startswith('multipart/'):
                            boundary = pars.get('boundary')
                            if boundary:
                                log.debug('Found boundary from headers: %s',
                                          boundary)
                                self._boundary = boundary

                    # Probe the line following the headers/content delimiter
                    try:
                        next_line = next(self._ilines)
                    except StopIteration:
                        log.debug('EOF detected')
                        part['content'] = StringIO('')
                    else:
                        if self._is_boundary(next_line):
                            log.debug('Content is empty for this part')
                            part['content'] = StringIO('')
                        else:
                            log.debug('Content ready for read')
                            self._ilines = chain([next_line], self._ilines)
                            part['content'] = StreamContent(self)

                    break

                # Keep reading headers line
                headers.append(rstripped_line)
                continue

        yield part

        if part is not None and not isinstance(part['content'], str):
            # Read the entire stream for this part to ensure the
            # cursor points to the end of the entire content or the
            # beginning of the next part, if exists
            try:
                flushed = part['content'].read()
            except Exception:
                log.exception('Error flushing part content')
                raise
            else:
                if flushed:
                    log.debug('Flushed unread part content of size %d bytes',
                              len(flushed))
                else:
                    log.debug('Part content was fully read before exit')
