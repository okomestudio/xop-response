# -*- coding: utf-8 -*-
import email
import logging
from pkg_resources import resource_string
from StringIO import StringIO

import pytest
import requests
import responses

from mime_streamer import MIMEStreamer
from mime_streamer import XOPResponseStreamer
from mime_streamer.exceptions import ParsingError


log = logging.getLogger(__name__)


def load_raw(resource):
    return resource_string(__name__, 'data/' + resource)


def test_text_html():
    raw = load_raw('text_html')
    parsed = email.message_from_string(raw)
    assert parsed.is_multipart() is False
    body = parsed.get_payload()

    streamer = MIMEStreamer(StringIO(raw))

    with streamer.get_next_part() as part:
        headers = part['headers']
        assert 'content-type' in headers
        assert headers['content-type'] == parsed.get('content-type')
        content = part['content'].read()
        assert content == body


def test_text_html_empty():
    raw = load_raw('text_html_empty')
    streamer = MIMEStreamer(StringIO(raw))
    with pytest.raises(ParsingError):
        with streamer.get_next_part():
            pass


def test_multipart_related_basic():
    raw = load_raw('multipart_related_basic')
    streamer = MIMEStreamer(StringIO(raw))

    with streamer.get_next_part() as part:
        headers = part['headers']
        assert 'Multipart/Related' in headers['content-type']
        assert 'start="<950120.aaCC@XIson.com>"' in headers['content-type']
        assert part['content'].read() == ''

    with streamer.get_next_part() as part:
        assert part['headers']['content-id'] == '<950120.aaCC@XIson.com>'
        assert '10\r\n34\r\n10' in part['content'].read()
        assert '' == part['content'].read()

    with streamer.get_next_part() as part:
        assert part['headers']['content-id'] == '<950120.aaCB@XIson.com>'
        assert 'gZHVja3MKRSBJIEUgSSB' in part['content'].read()
        assert '' == part['content'].read()


@responses.activate
def test_xop_example():
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

    xop = XOPResponseStreamer(resp)
    headers = xop.manifest_part['headers']
    assert headers['content-type'].startswith('application/xop+xml')
    assert headers['content-id'] == '<mymessage.xml@example.org>'

    with xop.get_next_part() as part:
        assert part['headers']['content-id'] == '<http://example.org/me.png>'
        assert part['content'].read() == '23580\r\n\r\n'

    with xop.get_next_part() as part:
        assert part['headers']['content-id'] == '<http://example.org/my.hsh>'
        assert part['content'].read() == '7923579\r\n\r\n'
