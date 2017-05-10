# -*- coding: utf-8 -*-
import logging
from contextlib import contextmanager
from email.parser import HeaderParser
from itertools import chain


log = logging.getLogger(__name__)


class Part(dict):
    pass


class IterableContent(object):

    def __init__(self, obj):
        assert isinstance(obj, MultipartRelatedStreamer)
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


class MultipartRelatedStreamer(object):

    def __init__(self, iter_lines, boundary, newline='\r\n'):
        self._newline = newline

        def it(s):
            for i in s:
                if i.endswith('\r\n'):
                    i = i.replace('\r\n', '')
                elif i.endswith('\n'):
                    i = i.replace('\n', '')
                yield i

        self._ilines = it(iter_lines)

        #ct = self.headers['content-type']
        #if not ct.startswith('multipart/related;'):
        #    raise ValueError('Response is not multipart/related content')
        #ct = self._parse_content_type(ct)
        # if ct['type'] != 'application/xop+xml':
        #     raise ValueError('Response type is not application/xop+xml')
        #self._start = ct['start']
        self._boundary = boundary

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def _parse_content_type(self, content_type):
        d = {}
        for item in content_type.split(';'):
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
        return line.startswith('--' + self._boundary)

    def iterparts(self):
        while 1:
            with self._parse_part() as part:
                if part is None:
                    break
                else:
                    yield part

    @contextmanager
    def _parse_part(self):

        def init_part():
            return Part({'type': None, 'content': None, 'headers': None})

        part = None
        headers = []

        while 1:
            line = next(self._ilines)
            log.debug('%r read: %s%s',
                      self, line[:50], '...' if len(line) > 50 else '')

            if self._is_boundary(line):
                # A boundary followed by an empty line indicates the
                # end of response content
                next_line = next(self._ilines)
                if next_line.strip() == '':
                    log.debug('XOP content ends')
                    part = None
                    break

                if part is not None:
                    log.debug('Ending part %r', part)
                    self._ilines = chain([line, next_line], self._ilines)
                    break

                else:
                    part = init_part()
                    log.debug('Creating a new part')
                    self._ilines = chain([next_line], self._ilines)
                    continue

            # Keep reading till the boundary is found and a new part
            # is initialized
            if part is None:
                continue

            if part['headers'] is None:
                s = line.strip()
                if s == '':
                    # An empty line here separates headers and content
                    log.debug('End headers %r', part['headers'])
                    p = HeaderParser()
                    part['headers'] = p.parsestr(self._newline.join(headers))
                    part['type'] = part['headers'].get('content-id')

                    self._ilines = chain(self._ilines)
                    part['content'] = IterableContent(self)
                    break

                headers.append(s)
                continue

        log.debug('Yielding part: %r', part)

        yield part

        log.debug('Leaving part context')

        if part is not None:
            try:
                s = part['content'].read()
                if s:
                    log.debug('Flushing remaining part content: %d', len(s))
                else:
                    log.debug('Part content was fully read before exit')
            except Exception:
                log.exception('Error flushing part content')

        log.debug('Left part context')


class XOPResponse(MultipartRelatedStreamer):

    def __init__(self, resp, newline='\r\n'):
        ct = resp.headers['content-type']
        if not ct.startswith('multipart/related;'):
            raise ValueError('Response is not multipart/related content')
        ct = self._parse_content_type(ct)
        boundary = ct['boundary']

        super(XOPResponse, self).__init__(
            iter_lins=resp.iter_lines(delimiter=newline),
            boundary=boundary,
            newline=newline)

        self._init()

    def _init(self):
        with self._parse_part() as part:
            part['content'] = part['content'].read()
        self._start_part = part
