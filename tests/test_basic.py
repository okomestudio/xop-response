# -*- coding: utf-8 -*-
import email
import logging
from pkg_resources import resource_string
try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

import pytest
import requests
import responses

from mime_streamer import MIMEStreamer
from mime_streamer import XOPResponseStreamer
from mime_streamer.exceptions import NoPartError
from mime_streamer.exceptions import ParsingError
from mime_streamer.utils import ensure_binary
from mime_streamer.utils import ensure_text


log = logging.getLogger(__name__)


def load_raw(resource):
    return resource_string(__name__, 'data/' + resource)


class TestMIMEStreamer(object):

    def test_text_html(self):
        raw = load_raw('text_html')
        parsed = email.message_from_string(ensure_text(raw))
        assert parsed.is_multipart() is False
        body = parsed.get_payload()

        streamer = MIMEStreamer(StringIO(raw))
        assert False
        with streamer.get_next_part() as part:
            headers = part.headers
            assert 'content-type' in headers
            assert headers['content-type'] == parsed.get('content-type')
            content = part.content.read()
            assert content == ensure_binary(body)

    def test_text_html_empty(self):
        raw = load_raw('text_html_empty')
        streamer = MIMEStreamer(StringIO(raw))
        with pytest.raises(ParsingError):
            with streamer.get_next_part():
                pass

    def test_multipart_related_basic(self):
        raw = load_raw('multipart_related_basic')
        streamer = MIMEStreamer(StringIO(raw))

        with streamer.get_next_part() as part:
            headers = part.headers
            assert 'Multipart/Related' in headers['content-type']
            assert 'start="<950120.aaCC@XIson.com>"' in headers['content-type']
            assert part.content.read() == b''

        with streamer.get_next_part() as part:
            assert part.headers['content-id'] == '<950120.aaCC@XIson.com>'
            assert b'10\r\n34\r\n10' in part.content.read()
            assert b'' == part.content.read()

        with streamer.get_next_part() as part:
            assert part.headers['content-id'] == '<950120.aaCB@XIson.com>'
            assert b'gZHVja3MKRSBJIEUgSSB' in part.content.read()
            assert b'' == part.content.read()

        with pytest.raises(NoPartError):
            with streamer.get_next_part() as part:
                assert True


@pytest.fixture
def post_url():
    url = 'http://mockapi/ep'
    content_type = ('multipart/related; '
                    'type="application/xop+xml"; '
                    'start="<mymessage.xml@example.org>"; '
                    'start-info="text/xml";\r\n\tboundary="MIME_boundary"')
    responses.add(
        responses.POST, url, status=200,
        body=resource_string(__name__, 'data/xop_example'),
        content_type=content_type)

    responses.start()

    yield url

    responses.stop()


class TestXOPResponseStreamer(object):

    def test_xop_example(self, post_url):
        resp = requests.post(post_url, stream=True)
        assert resp.status_code == 200

        streamer = XOPResponseStreamer(resp)
        headers = streamer.manifest_part.headers
        assert headers['content-type'].startswith('application/xop+xml')
        assert headers['content-id'] == '<mymessage.xml@example.org>'

        with streamer.get_next_part() as part:
            assert part.headers['content-id'] == '<http://example.org/me.png>'
            assert part.content.read() == b'23580\r\n\r\n'

        with streamer.get_next_part() as part:
            assert part.headers['content-id'] == '<http://example.org/my.hsh>'
            assert part.content.read() == b'7923579\r\n'
