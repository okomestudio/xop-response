# -*- coding: utf-8 -*-
import logging
from pkg_resources import resource_string
from StringIO import StringIO

import mock
import pytest
import requests
import responses

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


@responses.activate
def test_xop_response():
    url = 'http://mockapi/ep'
    content_type = ('multipart/related; '
                    'type="application/xop+xml"; '
                    'start="<mymessage.xml@example.org>"; '
                    'start-info="text/xml";\r\n\tboundary="MIME_boundary"')
    responses.add(
        responses.POST, url, status=200,
        body=resource_string(__name__, 'data/xop_example'),
        content_type=content_type)

    resp = requests.post(url)
    assert resp.status_code == 200

    xop = XOPResponse(resp)
    headers = xop.main_part['headers']
    assert headers['content-type'].startswith('application/xop+xml')
    assert headers['content-id'] == '<mymessage.xml@example.org>'

    with xop.get_next_part() as part:
        assert part['content-id'] == '<http://example.org/me.png>'
        assert part['content'].read() == '23580\r\n\r\n'

    with xop.get_next_part() as part:
        assert part['content-id'] == '<http://example.org/my.hsh>'
        assert part['content'].read() == '7923579\r\n\r\n'
