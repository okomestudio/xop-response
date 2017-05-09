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
from StringIO import StringIO

from .exceptions import NoPartError
from .exceptions import ParsingError


log = logging.getLogger(__name__)


NL = b'\r\n'
#: byte: The new line used to delimit lines


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


class Part(object):
    """A part constituting (multipart) message."""

    def __init__(self, headers=None):
        self._headers = headers or {}
        self._content = None

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, stream_content):
        self._content = stream_content

    @property
    def headers(self):
        return self._headers

    def flush_content(self):
        """Read the entire stream for this part to ensure the cursor points to
        the byte right after the end of the content or the part.

        """
        chunk_size = 256
        chunk = None
        flushed = 0
        try:
            while chunk != '':
                chunk = self._content.read(chunk_size)
                flushed += len(chunk)
        except Exception:
            log.exception('Error flushing part content')
            raise
        else:
            if flushed:
                log.debug('Flushed unread content of size %d bytes', flushed)
            else:
                log.debug('Part content was fully read before exit')

    def get_multipart_boundary(self):
        """Get the sentinel string indicating multipart boundary if exists."""
        if 'content-type' in self.headers:
            # Try looking for boundary info in this header
            pars = parse_content_type(self.headers['content-type'])
            if pars['mime-type'].startswith('multipart/'):
                return pars.get('boundary')


class StreamContent(object):
    """The iterator interface for reading content from a
    :class:`MIMEStreamer` object.

    Args:
        streamer (:class:`MIMEStreamer`): The streamer object
            representing the MIME content.

    """

    def __init__(self, streamer):
        self._streamer = streamer

        # The buffer storing current line
        self._buff = ''

        # The character position last read from `_buff`
        self._pos = 0

        # Boolean flag of whether EOF/boundary has been seen or not
        self._eof_seen = False

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def __iter__(self):
        return self

    def next(self):
        """Read a byte from stream.

        Returns:
            str: A single byte from the stream.

        Raises:
            StopIteration: When EOF is reached.

        """
        if self._eof_seen:
            raise StopIteration

        if self._pos + 1 >= len(self._buff):
            # The cursor points past the current line in the buffer,
            # so read in the new line
            line = self._streamer.stream.readline()
            log.debug('%r read: %r%s',
                      self, line[:76], '...' if len(line) > 76 else '')

            if self._streamer._is_boundary(line):
                log.debug('%r detected boundary', self)
                self._streamer.stream.rollback_line()
                self._eof_seen = True
                raise StopIteration
            elif line == '':
                self._eof_seen = True
                raise StopIteration

            self._buff = line
            self._pos = 0
        else:
            self._pos += 1

        return self._buff[self._pos]

    def read(self, n=-1):
        """Read at most `n` bytes, returned as string.

        Args:
            n (int, optional): If negative or omitted, read until EOF
                or part boundary is reached. If positive, at most `n`
                bytes will be returned.

        Returns:
            str: The bytes read from streamer.

        """
        assert n != 0
        buff = ''
        # iter(int, 1) is a way to create an infinite loop
        iterator = xrange(n) if n > 0 else iter(int, 1)
        for i in iterator:
            try:
                c = next(self)
            except StopIteration:
                break
            buff += c
        return buff


class StreamIO(object):
    """Wrapper for file-like object exposing only readline-related
    interface suitable for use with :class:`MIMEStreamer`.

    Args:
        stream (file): File-like object of byte stream.

    """

    def __init__(self, stream):
        self.stream = stream

        # Points to the head position of the line just read by
        # :meth:`StreamIO.readline`.
        self._head_of_last_line = None

    def __iter__(self):
        return self

    def next(self):
        return self.readline()

    def readline(self, length=None):
        """Read one entire line from the file.

        Returns:
            str: The line including the trailing newline.

        """
        if length is not None:
            raise NotImplementedError

        self._head_of_last_line = self.stream.tell()

        line = self.stream.readline()
        if line == '':
            return line

        while not line.endswith(NL):
            s = self.stream.readline()
            if s == '':
                break
            line += s

        return line

    def rollback_line(self):
        """Move the file's position to the head of previous line already read
        by :meth:`StreamIO.readline`.

        """
        self.stream.seek(self._head_of_last_line)

    def reaches_eof(self):
        """Test if the next line to be read reaches EOF."""
        next_line = self.readline()
        self.rollback_line()
        return next_line.rstrip() == ''


class MIMEStreamer(object):
    """The generic MIME content streamer.

    Args:
        stream (`file`): The `file`-like object that reads from a
            string buffer of content in the MIME format.
        boundary (`str`, optional): The MIME part boundary text.
        line_generator (generator, optional): A generator which takes
            in `stream` and generates lines.

    """

    def __init__(self, stream, boundary=None):
        self.stream = self.init_stream_io(stream)
        self._boundary = boundary or None

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def init_stream_io(self, stream):
        return StreamIO(stream)

    def _is_boundary(self, line):
        """Test if `line` is a part boundary."""
        return self._boundary and line.startswith('--' + self._boundary)

    @contextmanager
    def get_next_part(self):
        """Get the next part. Use this with the context manager (i.e., `with`
        statement).

        """
        # Assume the cursor is at the first char of headers of a part
        part = None
        headers = []

        while 1:
            line = self.stream.readline()
            log.debug('%r read: %r%s',
                      self, line[:76], '...' if len(line) > 76 else '')

            if self._is_boundary(line):
                # A boundary followed by an empty line indicates the
                # end of response content
                if self.stream.reaches_eof():
                    log.debug('Content ends')
                    break
                continue

            if part is None:
                # Still reading headers
                if line == '':
                    raise ParsingError('EOF while reading headers')

                if line != NL:
                    log.debug('%r read header line: %s', self, line[:-2])
                    headers.append(line)
                    continue

                # This empty line separates headers and content in
                # the current part
                log.debug('End headers %r', headers)
                headers = HeaderParser().parsestr(''.join(headers))
                log.debug('Parsed headers %r', headers.items())

                part = Part(headers)

                if not self._boundary:
                    boundary = part.get_multipart_boundary()
                    if boundary:
                        log.debug('Found boundary from headers: %s', boundary)
                        self._boundary = boundary

                # Probe the line following the headers/content delimiter
                if self.stream.reaches_eof():
                    log.debug('EOF detected')
                    part.content = StringIO('')
                else:
                    next_line = self.stream.readline()
                    if self._is_boundary(next_line):
                        log.debug('Content is empty for this part')
                        part.content = StringIO('')
                    else:
                        log.debug('Content ready for read')
                        self.stream.rollback_line()
                        part.content = StreamContent(self)

                break

        if part is None:
            raise NoPartError('No more part to read')

        try:
            yield part
        finally:
            if part is not None:
                part.flush_content()
