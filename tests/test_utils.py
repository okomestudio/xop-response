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

import pytest
import six

from mime_streamer.utils import ensure_binary


class EnsureTestCase(object):

    tfunc = NotImplemented

    def _test(self, trial, expected_value, expected_type):
        result = self.tfunc(trial)
        assert result == expected_value
        assert isinstance(result, expected_type)


class TestEnsureBinary(EnsureTestCase):

    tfunc = staticmethod(ensure_binary)

    @pytest.mark.parametrize('trial, expected_value, expected_type', [
        ('s', b's', bytes),
        (b's', b's', bytes),
        (u's', b's', bytes),
    ])
    def test(self, trial, expected_value, expected_type):
        self._test(trial, expected_value, expected_type)

    @pytest.mark.skipif(not six.PY2, reason='Skip if not Python 2.7')
    @pytest.mark.parametrize('trial, expected_value, expected_type', [
        ('s', b's', bytes),
        (b's', b's', bytes),
        (u's', b's', bytes),
    ])
    def test_py2(self, trial, expected_value, expected_type):
        self._test(trial, expected_value, expected_type)

    @pytest.mark.skipif(not six.PY3, reason='Skip if not Python 3.x')
    @pytest.mark.parametrize('trial, expected_value, expected_type', [
        ('s', b's', bytes),
        (b's', b's', bytes),
        (u's', b's', bytes),
    ])
    def test_py3(self, trial, expected_value, expected_type):
        self._test(trial, expected_value, expected_type)
