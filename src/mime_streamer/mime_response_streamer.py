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

from .mime_streamer import MIMEStreamer


log = logging.getLogger(__name__)


class MIMEResponseStreamer(MIMEStreamer):
    """An adapter for use with :class:`requests.Response`.

    Args:
        resp (:class:`requests.Response`): A response for an HTTP
            request for MIME content(s).
        boundary (`str`, optional): The MIME part boundary text. Leave
            this `None` for it to be determined from response headers.
        newline (`str`, optional): The newline delimiter used in
            response, defaults to '\r\n` and does not need to be changed.

    """

    def __init__(self, resp, boundary=None, newline='\r\n'):

        def line_generator(resp):
            for line in resp.iter_lines(delimiter=newline):
                yield line

        super(MIMEResponseStreamer, self).__init__(
            resp, boundary=boundary, line_generator=line_generator)


class XOPResponseStreamer(MIMEResponseStreamer):
    """An adapter for handling `applicatoin/xop+xml` contents (XML-binary
    optimized packaging).

    Args:
        resp (:class:`requests.Response`): A response for an HTTP
            request for `application/xop+xml` content(s).

    """

    def __init__(self, resp):
        ct = resp.headers['content-type']
        if not ct.lower().startswith('multipart/related'):
            raise ValueError('Response is not multipart/related content')

        ct = self._parse_content_type(ct)
        boundary = ct['boundary']

        super(XOPResponseStreamer, self).__init__(resp, boundary=boundary)

        self._load_first_part()

    def _load_first_part(self):
        """Initialize the instance with preloading the first part containing
        manifest.

        """
        # Forward to the first boundary line
        line = ''
        while not self._is_boundary(line):
            line = next(self._ilines)

        # ... to get to the first part containing manifest information
        with self.get_next_part() as part:
            part['content'] = part['content'].read()

        self.manifest = part
