# -*- coding: utf-8 -*-

import uuid
from unittest import mock

from rest_framework import status as http_status

from framework.exceptions import HTTPError

from addons.workflow import services
from addons.workflow.models import WorkflowEngine, WorkflowEngineKey
from tests.base import OsfTestCase


class ImportGatewayPublicKeysTests(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.engine = WorkflowEngine.objects.create(
            engine_id=str(uuid.uuid4()),
            gateway_base_url='https://gateway.example.com/',
            signing_kid='kid-test',
            verify_ssl=False,
        )

    def test_import_creates_or_updates_keys(self):
        payload = {
            'keys': [
                {
                    'kid': 'kid-1',
                    'alg': 'RS256',
                    'public_key': '-----BEGIN PUBLIC KEY-----\nAAA\n-----END PUBLIC KEY-----',
                },
                {
                    'kid': 'kid-2',
                    'alg': 'ES256',
                    'public_key': '-----BEGIN PUBLIC KEY-----\nBBB\n-----END PUBLIC KEY-----',
                },
            ],
        }

        client = mock.Mock()
        client.get_public_keyset.return_value = payload

        with mock.patch('addons.workflow.services.get_gateway_client', return_value=client) as mocked:
            imported = services.import_gateway_public_keys(self.engine)

        mocked.assert_called_once_with(self.engine.engine_id)
        self.assertEqual(imported, 2)

        stored_keys = WorkflowEngineKey.objects.filter(engine_id=self.engine.engine_id).order_by('kid')
        self.assertEqual(stored_keys.count(), 2)
        self.assertEqual(stored_keys[0].kid, 'kid-1')
        self.assertEqual(stored_keys[0].algorithm, 'RS256')
        self.assertTrue(stored_keys[0].is_active)
        self.assertIn('AAA', stored_keys[0].public_key)
        self.assertEqual(stored_keys[1].kid, 'kid-2')
        self.assertEqual(stored_keys[1].algorithm, 'ES256')

        # Update existing key with new material
        updated_payload = {
            'keys': [
                {
                    'kid': 'kid-1',
                    'alg': 'RS256',
                    'public_key': '-----BEGIN PUBLIC KEY-----\nNEW\n-----END PUBLIC KEY-----',
                },
            ],
        }
        client.get_public_keyset.return_value = updated_payload
        with mock.patch('addons.workflow.services.get_gateway_client', return_value=client):
            services.import_gateway_public_keys(self.engine)
        refreshed = WorkflowEngineKey.objects.get(engine_id=self.engine.engine_id, kid='kid-1')
        self.assertIn('NEW', refreshed.public_key)

    def test_import_raises_on_invalid_payload(self):
        client = mock.Mock()
        client.get_public_keyset.return_value = {'unexpected': []}

        with mock.patch('addons.workflow.services.get_gateway_client', return_value=client):
            with self.assertRaises(HTTPError) as context:
                services.import_gateway_public_keys(self.engine)

        self.assertEqual(context.exception.code, http_status.HTTP_502_BAD_GATEWAY)
