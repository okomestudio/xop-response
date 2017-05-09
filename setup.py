#!/usr/bin/env python2.7
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
import codecs
import os
import re
# from glob import glob
# from os.path import basename
# from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def find_meta(category, fpath='src/mime_streamer/__init__.py'):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, fpath), 'r') as f:
        package_root_file = f.read()
    matched = re.search(
        r"^__{}__\s+=\s+['\"]([^'\"]*)['\"]".format(category),
        package_root_file, re.M)
    if matched:
        return matched.group(1)
    raise Exception('Meta info string for {} undefined'.format(category))


setup(
    name='mime-streamer',
    description=('Stream IO for multipart MIME content'),
    author=find_meta('author'),
    author_email=find_meta('author_email'),
    license=find_meta('license'),
    version=find_meta('version'),
    platforms=['Linux'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities'],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    # py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    # include_package_data=True,
    # packages=['mime_related_streamer'],
    scripts=[],
    url='https://github.com/okomestudio/mime-streamer',
    install_requires=[])
