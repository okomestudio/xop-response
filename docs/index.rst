.. MIME Streamer documentation master file, created by
   sphinx-quickstart on Fri May 26 18:08:27 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

MIME Streamer
=============

Release v\ |version|

:mod:`mime-streamer` is a library for stream-read MIME content.
     
:mod:`mime-streamer` is licensed under the `MIT License (MIT)`_.

.. _MIT License (MIT): https://raw.githubusercontent.com/okomestudio/mime-streamer/master/LICENSE


Basic Usage
-----------

.. code-block:: python

    from io import BytesIO
    from pkg_resources import resource_string            
    from mime_streamer import MIMEStreamer

    raw = resource_string('tests', 'data/multipart_related_basic')

    streamer = MIMEStreamer(BytesIO(raw))

    with streamer.get_next_part() as part:
        headers = part.headers
        assert 'Multipart/Related' in headers['content-type']
        assert 'start="<950120.aaCC@XIson.com>"' in headers['content-type']
        assert b'' == part.content.read()

    with streamer.get_next_part() as part:
        assert '<950120.aaCC@XIson.com>' == part.headers['content-id']
        assert b'10\r\n34\r\n10' in part.content.read()

    with streamer.get_next_part() as part:
        assert '<950120.aaCB@XIson.com>' == part.headers['content-id']
        assert b'gZHVja3MKRSBJIEUgSSB' in part.content.read()

       
Installation
------------

.. code-block:: shell

   pip install mime-streamer



Note
----

The library currently is missing the following features:

- Nested multipart messages


API
---

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   mime_streamer


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
