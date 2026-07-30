# -*- coding: utf-8 -*-
"""Serializer tests for the Box addon."""
from unittest import mock
import pytest
from tests.base import OsfTestCase

from addons.iqbrims.utils import (
    embed_variables,
)


class TestEmbedVariables(OsfTestCase):

    def test_no_variables(self):
        assert (embed_variables('', {})) == ('')
        assert (embed_variables('Hello,\nThis is test', {})) == ('Hello,\nThis is test')

    def test_with_variables(self):
        variables = {'var1': 'Variable #1', 'var2': 'Variable #2'}
        assert (embed_variables('', variables)) == ('')
        assert (embed_variables('Hello,\nThis is test', variables)) == ('Hello,\nThis is test')
        assert (embed_variables('Hello,\nThis is ${var1}', variables)) == ('Hello,\nThis is Variable #1')
        assert (embed_variables('Hello,\nThis is ${var1} and ${var2}', variables)) == ('Hello,\nThis is Variable #1 and Variable #2')
        assert (embed_variables('Hello,\nThis is ${var1} and ${var1}', variables)) == ('Hello,\nThis is Variable #1 and Variable #1')

    def test_with_null_variables(self):
        variables = {'var1': 'Variable #1', 'var2': None}
        assert (embed_variables('', variables)) == ('')
        assert (embed_variables('Hello,\nThis is test', variables)) == ('Hello,\nThis is test')
        assert (embed_variables('Hello,\nThis is ${var1}', variables)) == ('Hello,\nThis is Variable #1')
        assert (embed_variables('Hello,\nThis is ${var1} and ${var2}', variables)) == ('Hello,\nThis is Variable #1 and null')
        assert (embed_variables('Hello,\nThis is ${var2} and ${var2}', variables)) == ('Hello,\nThis is null and null')
