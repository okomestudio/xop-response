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

from .exceptions import InvalidContentType
from .mime_streamer import MIMEStreamer
from .mime_streamer import NL
from .mime_streamer import parse_content_type


log = logging.getLogger(__name__)


class MIMEResponseStreamer(MIMEStreamer):
    """An adapter for use with :class:`requests.Response`.

    Args:
        resp (:class:`requests.Response`): A response to an HTTP
            request.

    """

    def __init__(self, resp):
        ct = resp.headers['content-type']
        if ct.lower().startswith('multipart/'):
            ct = parse_content_type(ct)
            boundary = ct['boundary']
            self._ct_params = ct
        else:
            boundary = None

        def line_generator(resp):
            for line in resp.iter_lines(delimiter=NL):
                yield line

        super(MIMEResponseStreamer, self).__init__(
            resp, boundary=boundary, line_generator=line_generator)


class XOPResponseStreamer(MIMEResponseStreamer):
    """An adapter for handling `XML-binary optimized packaging`_ contents
    via :class:`requests.Response`.

    This streamer loads the first part of the multipart message
    corresponding to `application/xop+xml` and makes it available as
    :attr:`XOPResponseStreamer.manifest_part`.

    Args:
        resp (:class:`requests.Response`): A response to an HTTP
            request.

    .. _XML-binary optimized packaging:
        https://www.w3.org/TR/xop10/

    """

    def __init__(self, resp):
        super(XOPResponseStreamer, self).__init__(resp)
        if self._ct_params['mime-type'].lower() != 'multipart/related':
            raise InvalidContentType(
                'Content must be of multipart/related type')
        if self._ct_params['type'].lower() != 'application/xop+xml':
            raise InvalidContentType(
                'Initial content type must be application/xop+xml')

        self._load_manifest_part()

    def _load_manifest_part(self):
        """Load the first part of application/xop+xml."""
        # Forward to the first boundary line
        line = ''
        while not self._is_boundary(line):
            line = self.read_next_line()

        with self.get_next_part() as part:
            content = part['content'].read()

        if not part['headers']['content-type'].lower().startswith(
                'application/xop+xml'):
            raise InvalidContentType(
                'Initial content type must be application/xop+xml')

        part['content'] = content
        self.manifest_part = part
