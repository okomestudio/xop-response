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
import logging
import re
from contextlib import contextmanager
from email.parser import HeaderParser
from itertools import chain


log = logging.getLogger(__name__)


class Part(dict):
    pass


class EmptyContent(object):
    def read(self, n=-1):
        return ''


class StreamContent(object):

    def __init__(self, obj):
        assert isinstance(obj, MIMEStreamer)
        self._obj = obj
        self._buff = ''
        self._pos = 0
        self._eof_seen = False

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def __iter__(self):
        return self

    def _is_boundary(self, line):
        return self._obj._is_boundary(line)

    def next(self):
        if self._eof_seen:
            raise StopIteration
        if self._pos >= len(self._buff) - 1:
            l = next(self._obj._ilines)
            log.debug('%r read: %s%s',
                      self, l[:50], '...' if len(l) > 50 else '')
            if self._is_boundary(l):
                log.debug('%r detected boundary', self)
                self._obj._ilines = chain([l], self._obj._ilines)
                self._eof_seen = True
                raise StopIteration
            self._buff = l + self._obj._newline
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


def _line_generator(s):
    for i in s:
        # NOTE (ts): Is this rstripping necessary?
        if i.endswith('\r\n'):
            i = i.replace('\r\n', '')
        elif i.endswith('\n'):
            i = i.replace('\n', '')
        yield i


class MIMEStreamer(object):
    """Generic MIME content streamer.

    Args:
        stream (`file`): The `file`-like object that reads from a
            string buffer.
        boundary (`str`, optional): The MIME part boundary text.
        line_generator (generator, optional): A generator which takes
            in `stream` and generates lines.
        newline (`str`, optional): The newline delimiter used in
            response, defaults to '\r\n` and does not need to be changed.

    """

    def __init__(self, stream, boundary=None, line_generator=None,
                 newline='\r\n'):
        self._newline = newline
        self._ilines = (line_generator or _line_generator)(stream)

        if not boundary:
            # Look for boundary definition in the headers of the very
            # initial part
            pass

        #ct = self.headers['content-type']
        #if not ct.startswith('multipart/related;'):
        #    raise ValueError('Response is not multipart/related content')
        #ct = self._parse_content_type(ct)
        # if ct['type'] != 'application/xop+xml':
        #     raise ValueError('Response type is not application/xop+xml')
        #self._start = ct['start']

        self._boundary = boundary or None

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    re_split_content_type = re.compile(r'(;|\r\n)')

    def _parse_content_type(self, content_type):
        items = self.re_split_content_type.split(content_type)
        d = {'mime-type': items.pop(0)}
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

        def init_part():
            return Part({'content-id': None, 'content': None, 'headers': None})

        # Assume the cursor is initialized to the first char of headers
        part = init_part()
        headers = []

        while 1:
            line = next(self._ilines)
            log.debug('%r read: %s%s',
                      self, line[:50], '...' if len(line) > 50 else '')

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
                    log.debug('XOP content ends')
                    part = None
                    break

                self._ilines = chain([next_line], self._ilines)
                continue

            # Keep reading till the boundary is found and a new part
            # is initialized
            if part is None:
                continue

            if part['headers'] is None:
                s = line.rstrip()
                if s == '':
                    # An empty line here separates headers and content
                    log.debug('End headers %r', headers)

                    # User helper to parse headers properly
                    p = HeaderParser()
                    part['headers'] = p.parsestr(self._newline.join(headers))
                    part['content-id'] = part['headers'].get('content-id')

                    if not self._boundary:
                        # Try looking for boundary info in this header
                        if 'content-type' in part['headers']:
                            pars = self._parse_content_type(
                                part['headers']['content-type'])
                            boundary = pars.get('boundary')
                            if boundary:
                                log.debug('Found boundary from headers: %s',
                                          boundary)
                                self._boundary = boundary

                    next_line = next(self._ilines)
                    if self._is_boundary(next_line):
                        log.debug('Content is empty for this part')
                        part['content'] = EmptyContent()
                    else:
                        log.debug('Content ready for read')
                        self._ilines = chain([next_line], self._ilines)
                        part['content'] = StreamContent(self)
                    break

                headers.append(s)
                continue

        log.debug('Yielding part: %r', part)

        yield part

        log.debug('Leaving part context')

        if part is not None and not isinstance(part['content'], str):
            # Read the entire stream for this part to ensure the
            # cursor points to the end of the entire content or the
            # beginning of the next part if exists
            try:
                s = part['content'].read()
            except Exception:
                log.exception('Error flushing part content')
                raise
            else:
                if s:
                    log.debug('Flushed unread part content of size %d bytes',
                              len(s))
                else:
                    log.debug('Part content was fully read before exit')

        log.debug('Left part context')
