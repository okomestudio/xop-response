# -*- coding: utf-8 -*-
import logging
from pkg_resources import resource_string
from StringIO import StringIO

import mock
import pytest
import requests

from mime_related_streamer.multipart_related_streamer \
    import MultipartRelatedStreamer
from mime_related_streamer.multipart_related_streamer \
    import XOPResponse


log = logging.getLogger(__name__)


@pytest.fixture
def content():
    return resource_string(__name__, 'data/multipart_related_basic')


def test_multipart_related_streamer(content):
    mrs = MultipartRelatedStreamer(StringIO(content))

    with mrs.get_next_part() as part:
        assert part['content-id'] is None
        headers = part['headers']
        assert 'Multipart/Related' in headers['content-type']
        assert 'start="<950120.aaCC@XIson.com>"' in headers['content-type']
        assert part['content'].read() == ''

    with mrs.get_next_part() as part:
        assert part['content-id'] == '<950120.aaCC@XIson.com>'
        assert '10\r\n34\r\n10' in part['content'].read()
        assert '' == part['content'].read()

    with mrs.get_next_part() as part:
        assert part['content-id'] == '<950120.aaCB@XIson.com>'
        assert 'gZHVja3MKRSBJIEUgSSB' in part['content'].read()
        assert '' == part['content'].read()


@mock.patch.object(requests, 'post')
def test_xop_response(post):
    post.return_value = resource_string(__name__, 'data/multipart_related_basic')

    resp = requests.post()
    xop = XOPResponse(resp)
