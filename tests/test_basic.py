import pytest

from mime_related_streamer.mp_related_streamer import MultipartRelatedStreamer


content = '''Content-Type: Multipart/Related; boundary=example-1
        start="<950120.aaCC@XIson.com>";
        type="Application/X-FixedRecord"
        start-info="-o ps"

--example-1
Content-Type: Application/X-FixedRecord
Content-ID: <950120.aaCC@XIson.com>

25
10
34
10
25
21
26
10
--example-1
Content-Type: Application/octet-stream
Content-Description: The fixed length records
Content-Transfer-Encoding: base64
Content-ID: <950120.aaCB@XIson.com>

T2xkIE1hY0RvbmFsZCBoYWQgYSBmYXJtCkUgSS
BFIEkgTwpBbmQgb24gaGlzIGZhcm0gaGUgaGFk
IHNvbWUgZHVja3MKRSBJIEUgSSBPCldpdGggYS
BxdWFjayBxdWFjayBoZXJlLAphIHF1YWNrIHF1
YWNrIHRoZXJlLApldmVyeSB3aGVyZSBhIHF1YW
NrIHF1YWNrCkUgSSBFIEkgTwo=

--example-1--
'''.replace('\n', '\r\n')


def test():
    import StringIO
    
    mrs = MultipartRelatedStreamer(StringIO.StringIO(content), 'example-1')
    for part in mrs.iterparts():
        print repr(part)
        print part['content'].read()
    assert 0
