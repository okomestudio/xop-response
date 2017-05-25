MIME Streamer
=============

MIME content stream reader for Python.

`mime-streamer` is licensed under the `MIT License (MIT)`_.

.. _MIT License (MIT): https://raw.githubusercontent.com/okomestudio/pyrediq/development/LICENSE.txt


Basic Usage
-----------

.. code-block:: python

    from StringIO import StringIO
    from mime_streamer import MIMEStreamer

    raw = '\r\n'.join([
        'Content-Type: Multipart/Related; boundary=example-1',
        '        start="<950120.aaCC@XIson.com>";',
        '        type="Application/X-FixedRecord"',
        '        start-info="-o ps"',
        '',
        '--example-1',
        'Content-Type: Application/X-FixedRecord',
        'Content-ID: <950120.aaCC@XIson.com>',
        '',
        '25',
        '10',
        '34',
        '10',
        '25',
        '21',
        '26',
        '10',
        '--example-1',
        'Content-Type: Application/octet-stream',
        'Content-Description: The fixed length records',
        'Content-Transfer-Encoding: base64',
        'Content-ID: <950120.aaCB@XIson.com>',
        '',
        'T2xkIE1hY0RvbmFsZCBoYWQgYSBmYXJtCkUgSS',
        'BFIEkgTwpBbmQgb24gaGlzIGZhcm0gaGUgaGFk',
        'IHNvbWUgZHVja3MKRSBJIEUgSSBPCldpdGggYS',
        'BxdWFjayBxdWFjayBoZXJlLAphIHF1YWNrIHF1',
        'YWNrIHRoZXJlLApldmVyeSB3aGVyZSBhIHF1YW',
        'NrIHF1YWNrCkUgSSBFIEkgTwo=',
        '',
        '--example-1--'])

    streamer = MIMEStreamer(StringIO(raw))

    with streamer.get_next_part() as part:
        headers = part.headers
        assert 'Multipart/Related' in headers['content-type']
        assert 'start="<950120.aaCC@XIson.com>"' in headers['content-type']
        assert part.content.read() == ''

    with streamer.get_next_part() as part:
        assert part.headers['content-id'] == '<950120.aaCC@XIson.com>'
        assert '10\r\n34\r\n10' in part.content.read()

    with streamer.get_next_part() as part:
        assert part.headers['content-id'] == '<950120.aaCB@XIson.com>'
        assert 'gZHVja3MKRSBJIEUgSSB' in part.content.read()

       
Installation
------------

.. code-block::

   pip install mime-streamer


Note
----

The library currently is missing the following features:

- Nested multipart messages
- Python 3.x
