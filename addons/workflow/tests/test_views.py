# -*- coding: utf-8 -*-
"""Integration tests for workflow engine views."""

import tempfile
import uuid
from pathlib import Path
from unittest import mock

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from rest_framework import status as http_status

from framework.auth.core import Auth

from addons.workflow import settings as workflow_settings
from addons.workflow.gateway_client import WorkflowGatewayClientError
from addons.workflow.models import (
    WorkflowActivation,
    WorkflowDefinitionSnapshot,
    WorkflowEngine,
    WorkflowTemplate,
    WorkflowRun,
)
from osf_tests.factories import AuthUserFactory, InstitutionFactory, ProjectFactory
from tests.base import OsfTestCase
from website.util import api_url_for


pytestmark = pytest.mark.django_db


class WorkflowEngineViewTests(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.list_engines_url = api_url_for('list_engines')
        self.gateway_keyset_url = api_url_for('gateway_keyset')
        self.upsert_engine_url = api_url_for('upsert_engine')

    @staticmethod
    def _engine_keys_url(engine_id: str) -> str:
        return api_url_for('list_engine_keys', engine_id=engine_id)

    @staticmethod
    def _engine_definitions_url(engine_id: str) -> str:
        return api_url_for('list_engine_definitions', engine_id=engine_id)

    @staticmethod
    def _create_engine(owner=None, institution=None) -> WorkflowEngine:
        engine_id = str(uuid.uuid4())
        institution = institution or InstitutionFactory()
        return WorkflowEngine.objects.create(
            engine_id=engine_id,
            gateway_base_url=f'https://{engine_id}.example.com/api/',
            signing_kid=f'{engine_id}-kid',
            created_by=owner,
            institution=institution,
        )

    @staticmethod
    def _template_url(node) -> str:
        return api_url_for('upsert_template', pid=node._id)

    @staticmethod
    def _create_project_with_workflow(owner):
        node = ProjectFactory(creator=owner)
        node.add_addon('workflow', auth=Auth(owner))
        return node

    @staticmethod
    def _activation_url(route: str, node, template) -> str:
        template_id = template._id if hasattr(template, '_id') else template
        return api_url_for(route, pid=node._id, template_id=template_id)

    @staticmethod
    def _run_url(node, template) -> str:
        template_id = template._id if hasattr(template, '_id') else template
        return api_url_for('start_run', pid=node._id, template_id=template_id)

    @staticmethod
    def _run_detail_url(node, run_id: int) -> str:
        return api_url_for('cancel_run', pid=node._id, run_id=run_id)

    @staticmethod
    def _tasks_url(node) -> str:
        return api_url_for('list_tasks', pid=node._id)

    @staticmethod
    def _task_detail_url(node, task_id: str) -> str:
        return api_url_for('retrieve_task', pid=node._id, task_id=task_id)

    @staticmethod
    def _task_action_url(node, task_id: str) -> str:
        return api_url_for('submit_task_action', pid=node._id, task_id=task_id)

    def _configure_gateway_keys(self, kid: str = 'test-key') -> str:
        original_specs = workflow_settings.RDM_TO_WORKFLOW_GATEWAY_KEYS
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )

        private_key_path = Path(tempdir.name) / 'rdm.key'
        public_key_path = Path(tempdir.name) / 'rdm.pub'

        private_key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        public_key_path.write_bytes(
            private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        workflow_settings.RDM_TO_WORKFLOW_GATEWAY_KEYS = [
            {
                'kid': kid,
                'alg': 'RS256',
                'private_key_path': str(private_key_path),
                'public_key_path': str(public_key_path),
            },
        ]
        self.addCleanup(
            lambda: setattr(
                workflow_settings,
                'RDM_TO_WORKFLOW_GATEWAY_KEYS',
                original_specs,
            )
        )
        return kid

    def test_list_engines_limits_to_owner_and_affiliation(self):
        user = AuthUserFactory()
        shared_institution = InstitutionFactory()
        user.affiliated_institutions.add(shared_institution)

        same_institution_owner = AuthUserFactory()
        same_institution_owner.affiliated_institutions.add(shared_institution)

        other_institution = InstitutionFactory()
        other_owner = AuthUserFactory()
        other_owner.affiliated_institutions.add(other_institution)

        own_engine = self._create_engine(owner=user)
        shared_engine = self._create_engine(owner=same_institution_owner)
        other_engine = self._create_engine(owner=other_owner)
        ownerless_engine = self._create_engine()

        response = self.app.get(self.list_engines_url, auth=user.auth)
        engine_ids = {item['engine_id'] for item in response.json['data']}

        assert engine_ids == {own_engine.engine_id, shared_engine.engine_id}
        assert other_engine.engine_id not in engine_ids
        assert ownerless_engine.engine_id not in engine_ids
        assert response.json['meta']['is_super_admin'] is False
        assert response.json['meta']['is_institutional_admin'] is False

    def test_list_engines_applies_same_rules_to_admin(self):
        admin = AuthUserFactory()
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        other = AuthUserFactory()
        own_engine = self._create_engine(owner=admin)
        other_engine = self._create_engine(owner=other)
        ownerless_engine = self._create_engine()

        response = self.app.get(self.list_engines_url, auth=admin.auth)
        engine_ids = {item['engine_id'] for item in response.json['data']}

        assert engine_ids == {own_engine.engine_id}
        assert other_engine.engine_id not in engine_ids
        assert ownerless_engine.engine_id not in engine_ids
        assert response.json['meta']['is_super_admin'] is True
        assert response.json['meta']['is_institutional_admin'] is False

    def test_list_engine_definitions_returns_payload(self):
        owner = AuthUserFactory()
        engine = self._create_engine(owner=owner)

        mock_client = mock.Mock()
        mock_client.list_process_definitions.return_value = {
            'data': [
                {
                    'id': 'workflow:definition:alpha',
                    'name': 'Process Alpha',
                    'version': 3,
                    'key': 'alpha',
                    'category': 'demo',
                    'deploymentId': 'deploy-1',
                    'description': 'Example definition',
                }
            ],
            'total': 1,
        }

        with mock.patch('addons.workflow.views.get_gateway_client', return_value=mock_client):
            response = self.app.get(
                self._engine_definitions_url(engine.engine_id),
                auth=owner.auth,
            )

        assert response.status_code == http_status.HTTP_200_OK
        payload = response.json
        assert payload['total'] == 1
        definitions = payload['data']
        assert len(definitions) == 1
        assert definitions[0]['definition_id'] == 'workflow:definition:alpha'
        assert definitions[0]['definition_name'] == 'Process Alpha'
        assert definitions[0]['definition_version'] == 3
        assert definitions[0]['definition_deployment_id'] == 'deploy-1'

    def test_retrieve_engine_allows_owner(self):
        user = AuthUserFactory()
        engine = self._create_engine(owner=user)

        response = self.app.get(
            api_url_for('retrieve_engine', engine_id=engine.engine_id),
            auth=user.auth,
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.json['data']['engine_id'] == engine.engine_id

    def test_retrieve_engine_allows_affiliated_user(self):
        user = AuthUserFactory()
        shared_institution = InstitutionFactory()
        user.affiliated_institutions.add(shared_institution)

        owner = AuthUserFactory()
        owner.affiliated_institutions.add(shared_institution)

        engine = self._create_engine(owner=owner)

        response = self.app.get(
            api_url_for('retrieve_engine', engine_id=engine.engine_id),
            auth=user.auth,
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.json['data']['engine_id'] == engine.engine_id

    def test_retrieve_engine_denies_unrelated_user(self):
        user = AuthUserFactory()
        other = AuthUserFactory()
        engine = self._create_engine(owner=other)

        response = self.app.get(
            api_url_for('retrieve_engine', engine_id=engine.engine_id),
            auth=user.auth,
            expect_errors=True,
        )
        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    def test_admin_requirement_allows_staff_but_not_regular_user(self):
        staff_user = AuthUserFactory()
        staff_user.is_staff = True
        staff_user.is_superuser = False
        staff_user.save()

        engine = self._create_engine(owner=staff_user)

        response = self.app.get(self._engine_keys_url(engine.engine_id), auth=staff_user.auth)
        assert response.status_code == http_status.HTTP_200_OK
        assert response.json == {'data': []}

        regular_user = AuthUserFactory()
        response = self.app.get(
            self._engine_keys_url(engine.engine_id),
            auth=regular_user.auth,
            expect_errors=True,
        )
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_engine_keys_rejects_staff_without_visibility(self):
        owner = AuthUserFactory()
        engine = self._create_engine(owner=owner)

        staff_user = AuthUserFactory()
        staff_user.is_staff = True
        staff_user.is_superuser = False
        staff_user.save()

        response = self.app.get(
            self._engine_keys_url(engine.engine_id),
            auth=staff_user.auth,
            expect_errors=True,
        )

        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    def test_gateway_keyset_returns_configured_keys(self):
        self._configure_gateway_keys()

        response = self.app.get(self.gateway_keyset_url)
        assert response.status_code == http_status.HTTP_200_OK
        payload = response.json
        assert payload['keys'][0]['kid'] == 'test-key'
        assert payload['keys'][0]['alg'] == 'RS256'
        assert 'BEGIN PUBLIC KEY' in payload['keys'][0]['public_key']

    def test_gateway_keyset_returns_503_when_unconfigured(self):
        original_specs = workflow_settings.RDM_TO_WORKFLOW_GATEWAY_KEYS
        workflow_settings.RDM_TO_WORKFLOW_GATEWAY_KEYS = []
        self.addCleanup(
            lambda: setattr(
                workflow_settings,
                'RDM_TO_WORKFLOW_GATEWAY_KEYS',
                original_specs,
            )
        )

        response = self.app.get(self.gateway_keyset_url, expect_errors=True)
        assert response.status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE

    def test_register_workflow_success(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)
        engine = self._create_engine(owner=owner)
        definition_id = 'process-definition-1'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Example Process',
            version=1,
        )

        token_settings = {'aud': 'gateway', 'scope': 'workflow::delegate'}
        response = self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
                'label': 'My Workflow',
                'description': 'Test template',
                'token_settings': token_settings,
            },
            auth=owner.auth,
        )

        assert response.status_code == http_status.HTTP_201_CREATED
        payload = response.json
        assert payload['created'] is True
        data = payload['data']
        assert data['engine_id'] == engine.engine_id
        assert data['definition_id'] == definition_id
        assert data['label'] == 'My Workflow'
        assert data['token_settings'] == token_settings
        assert data['is_enabled'] is False
        assert data['activation_id'] is None
        assert data['activation_activated_by'] is None

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )
        assert not WorkflowActivation.objects.filter(
            node=node,
            template=template,
        ).exists()

    def test_register_workflow_rejects_invalid_engine_id(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        response = self.app.post_json(
            self._template_url(node),
            {
                'engine_id': 'not-a-uuid',
                'definition_id': 'definition-1',
            },
            auth=owner.auth,
            expect_errors=True,
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_register_workflow_requires_write_permission(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)
        engine = self._create_engine(owner=owner)
        definition_id = 'process-definition-2'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Example Process',
            version=1,
        )

        outsider = AuthUserFactory()
        response = self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=outsider.auth,
            expect_errors=True,
        )

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_register_workflow_reuses_existing_template(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)
        engine = self._create_engine(owner=owner)
        definition_id = 'process-definition-3'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Example Process',
            version=1,
        )

        # First call creates the template
        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        # Second call should reuse existing record
        response = self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
                'label': 'Updated Label',
            },
            auth=owner.auth,
        )

        assert response.status_code == http_status.HTTP_200_OK
        assert response.json['created'] is False
        data = response.json['data']
        assert data['label'] == 'Updated Label'

    def test_register_engine_rejects_non_uuid_engine_id(self):
        admin = AuthUserFactory()
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        kid = self._configure_gateway_keys()

        response = self.app.post_json(
            self.upsert_engine_url,
            {
                'engine_id': 'not-a-uuid',
                'gateway_base_url': 'https://workflow.example/api/',
                'signing_kid': kid,
            },
            auth=admin.auth,
            expect_errors=True,
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_register_engine_accepts_uuid_and_normalizes(self):
        admin = AuthUserFactory()
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        kid = self._configure_gateway_keys()

        raw_engine_id = str(uuid.uuid4()).upper()
        response = self.app.post_json(
            self.upsert_engine_url,
            {
                'engine_id': raw_engine_id,
                'gateway_base_url': 'https://workflow.example/api/',
                'signing_kid': kid,
                'token_lifetime_seconds': 600,
                'request_timeout': 15,
            },
            auth=admin.auth,
        )

        assert response.status_code == http_status.HTTP_201_CREATED
        stored_id = response.json['data']['engine_id']
        assert stored_id == str(uuid.UUID(raw_engine_id))
        assert WorkflowEngine.objects.filter(engine_id=stored_id).exists()
        WorkflowEngine.objects.filter(engine_id=stored_id).delete()

    def test_list_templates_includes_local_and_shared(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)
        engine = self._create_engine(owner=owner)
        definition_id_local = 'process-definition-local'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id_local,
            definition_key='process-def-key',
            name='Local Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id_local,
                'label': 'Local Flow',
            },
            auth=owner.auth,
        )

        shared_owner = AuthUserFactory()
        shared_node = self._create_project_with_workflow(shared_owner)
        shared_node.add_contributor(owner, auth=Auth(shared_owner), save=True)
        engine_shared = self._create_engine(owner=shared_owner)
        definition_id_shared = 'process-definition-shared'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine_shared,
            definition_id=definition_id_shared,
            definition_key='process-def-key',
            name='Shared Process',
            version=1,
        )
        self.app.post_json(
            self._template_url(shared_node),
            {
                'engine_id': engine_shared.engine_id,
                'definition_id': definition_id_shared,
                'label': 'Shared Flow',
            },
            auth=shared_owner.auth,
        )

        hidden_owner = AuthUserFactory()
        hidden_node = self._create_project_with_workflow(hidden_owner)
        engine_hidden = self._create_engine(owner=hidden_owner)
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine_hidden,
            definition_id='process-definition-hidden',
            definition_key='process-def-key',
            name='Hidden Process',
            version=1,
        )
        self.app.post_json(
            self._template_url(hidden_node),
            {
                'engine_id': engine_hidden.engine_id,
                'definition_id': 'process-definition-hidden',
            },
            auth=hidden_owner.auth,
        )

        response = self.app.get(
            api_url_for('list_templates', pid=node._id),
            auth=owner.auth,
        )
        assert response.status_code == http_status.HTTP_200_OK
        templates = response.json['data']
        guids = {entry['definition_id']: entry for entry in templates}
        assert definition_id_local in guids
        assert definition_id_shared in guids
        assert 'process-definition-hidden' not in guids
        assert guids[definition_id_local]['is_local'] is True
        assert guids[definition_id_shared]['is_local'] is False
        assert guids[definition_id_local]['node_id'] == node._id
        assert guids[definition_id_shared]['node_id'] == shared_node._id
        assert guids[definition_id_local]['visibility'] == WorkflowTemplate.VISIBILITY_PROJECT
        assert guids[definition_id_shared]['visibility'] == WorkflowTemplate.VISIBILITY_PROJECT
        assert guids[definition_id_local]['is_enabled'] is False
        assert guids[definition_id_shared]['is_enabled'] is False
        assert guids[definition_id_local]['activation_id'] is None
        assert guids[definition_id_shared]['activation_id'] is None

    def test_list_templates_includes_institution_visibility_for_affiliates(self):
        owner = AuthUserFactory()
        shared_node = self._create_project_with_workflow(owner)
        viewer = AuthUserFactory()
        viewer_node = self._create_project_with_workflow(viewer)
        institution = InstitutionFactory()
        owner.affiliated_institutions.add(institution)
        viewer.affiliated_institutions.add(institution)
        shared_node.affiliated_institutions.add(institution)

        engine = self._create_engine(owner=owner, institution=institution)
        definition_id = 'institution-visible-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Institution Visible Flow',
            version=1,
        )

        self.app.post_json(
            self._template_url(shared_node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
                'label': 'Institution Template',
                'visibility': WorkflowTemplate.VISIBILITY_INSTITUTION,
            },
            auth=owner.auth,
        )

        response = self.app.get(
            api_url_for('list_templates', pid=viewer_node._id),
            auth=viewer.auth,
        )
        data = response.json['data']
        guids = {entry['definition_id']: entry for entry in data}
        assert definition_id in guids
        assert guids[definition_id]['visibility'] == WorkflowTemplate.VISIBILITY_INSTITUTION

    def test_list_templates_includes_public_visibility_for_all_users(self):
        owner = AuthUserFactory()
        shared_node = self._create_project_with_workflow(owner)
        viewer = AuthUserFactory()
        viewer_node = self._create_project_with_workflow(viewer)

        engine = self._create_engine(owner=owner)
        definition_id = 'public-visible-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Public Visible Flow',
            version=1,
        )

        self.app.post_json(
            self._template_url(shared_node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
                'label': 'Public Template',
                'visibility': WorkflowTemplate.VISIBILITY_PUBLIC,
            },
            auth=owner.auth,
        )

        response = self.app.get(
            api_url_for('list_templates', pid=viewer_node._id),
            auth=viewer.auth,
        )
        data = response.json['data']
        guids = {entry['definition_id']: entry for entry in data}
        assert definition_id in guids
        assert guids[definition_id]['visibility'] == WorkflowTemplate.VISIBILITY_PUBLIC

    def test_engine_endpoints_reject_invalid_identifier(self):
        user = AuthUserFactory()
        response = self.app.get(
            api_url_for('retrieve_engine', engine_id='invalid-id'),
            auth=user.auth,
            expect_errors=True,
        )
        assert response.status_code == http_status.HTTP_404_NOT_FOUND

        admin = AuthUserFactory()
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        response = self.app.get(
            self._engine_keys_url('invalid-id'),
            auth=admin.auth,
            expect_errors=True,
        )
        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    def test_activation_lifecycle_for_shared_template(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        shared_owner = AuthUserFactory()
        shared_node = self._create_project_with_workflow(shared_owner)
        shared_node.add_contributor(owner, auth=Auth(shared_owner), save=True)

        engine_shared = self._create_engine(owner=shared_owner)
        definition_id_shared = 'activation-shared-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine_shared,
            definition_id=definition_id_shared,
            definition_key='process-def-key',
            name='Shared Activation Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(shared_node),
            {
                'engine_id': engine_shared.engine_id,
                'definition_id': definition_id_shared,
                'label': 'Shared Flow',
            },
            auth=shared_owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=shared_node,
            definition__definition_id=definition_id_shared,
        )

        activation_payload = {'is_enabled': True, 'token_settings': {'pat': 'secret-token'}}
        response = self.app.put_json(
            self._activation_url('upsert_activation', node, template),
            activation_payload,
            auth=owner.auth,
        )
        assert response.status_code == http_status.HTTP_201_CREATED
        data = response.json['data']
        assert data['is_enabled'] is True
        assert data['token_settings'] == activation_payload['token_settings']
        assert data['activated_by'] == owner._id

        activation = WorkflowActivation.objects.get(node=node, template=template)
        assert activation.is_enabled is True
        assert activation.token_settings == activation_payload['token_settings']

        response = self.app.get(
            self._activation_url('retrieve_activation', node, template),
            auth=owner.auth,
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.json['data']['is_enabled'] is True

        response = self.app.delete(
            self._activation_url('deactivate_activation', node, template),
            auth=owner.auth,
        )
        assert response.status_code == http_status.HTTP_204_NO_CONTENT
        activation.refresh_from_db()
        assert activation.is_enabled is False

        response = self.app.put_json(
            self._activation_url('upsert_activation', node, template),
            {'is_enabled': True},
            auth=owner.auth,
        )
        assert response.status_code == http_status.HTTP_200_OK
        activation.refresh_from_db()
        assert activation.is_enabled is True
        assert activation.token_settings == activation_payload['token_settings']

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    @mock.patch('addons.workflow.tasks.start_workflow_process_task')
    def test_start_run_enqueues_celery_job(self, mock_task, mock_enqueue):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'start-process-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Process to Start',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )

        signature = mock.Mock(name='signature')
        mock_task.si.return_value = signature

        payload = {
            'label': 'Custom Run Label',
        }

        response = self.app.post_json(
            self._run_url(node, template),
            payload,
            auth=owner.auth,
        )

        assert response.status_code == http_status.HTTP_202_ACCEPTED
        data = response.json['data']
        run_id = int(data['id'])
        assert data['status'] == 'queued'
        assert data['engine_process_id'] is None
        assert data['label'] == 'Custom Run Label'

        run = WorkflowRun.objects.get(id=run_id)
        assert run.status == WorkflowRun.STATUS_QUEUED

        mock_task.si.assert_called_once_with(run_id)
        mock_enqueue.assert_called_once_with(signature)

    def test_list_runs_returns_recent_runs(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'listing-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Listable Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )

        response = self.app.post_json(
            self._run_url(node, template),
            {'parameters': {'alpha': 'beta'}},
            auth=owner.auth,
        )
        assert response.status_code == http_status.HTTP_202_ACCEPTED

        listing = self.app.get(
            api_url_for('list_runs', pid=node._id),
            auth=owner.auth,
        )
        assert listing.status_code == http_status.HTTP_200_OK
        data = listing.json['data']
        assert len(data) == 1
        record = data[0]
        assert record['status'] == WorkflowRun.STATUS_QUEUED
        assert record['context']['parameters'] == {'alpha': 'beta'}

    @mock.patch('addons.workflow.services.get_gateway_client')
    def test_list_runs_marks_unknown_when_history_missing(self, mock_get_client):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'missing-history-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='History Missing Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )
        activation = WorkflowActivation.objects.get(node=node, template=template)

        run = WorkflowRun.objects.create(
            node=node,
            template=template,
            activation=activation,
            engine=engine,
            started_by=owner,
            label='Missing history run',
            business_key=f'rdm:node:{node._id}',
            engine_process_id='proc-missing',
            engine_definition_id=definition_id,
            status=WorkflowRun.STATUS_RUNNING,
        )

        client = mock.Mock()
        mock_get_client.return_value = client
        not_found_error = WorkflowGatewayClientError(
            http_status.HTTP_404_NOT_FOUND,
            'Not Found',
        )
        client.get_historic_process_instance.side_effect = not_found_error

        listing = self.app.get(
            api_url_for('list_runs', pid=node._id),
            auth=owner.auth,
        )

        assert listing.status_code == http_status.HTTP_200_OK
        payload = listing.json['data'][0]
        assert payload['status'] == WorkflowRun.STATUS_UNKNOWN

        run.refresh_from_db()
        assert run.status == WorkflowRun.STATUS_UNKNOWN
        history_errors = run.metadata.get('history_errors')
        assert isinstance(history_errors, list) and history_errors

    def test_cancel_run_by_admin_changes_status(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'cancel-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Cancelable Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )

        start_response = self.app.post_json(
            self._run_url(node, template),
            {},
            auth=owner.auth,
        )
        run_id = int(start_response.json['data']['id'])

        cancel_response = self.app.delete(
            f"{self._run_detail_url(node, run_id)}?reason=manual",
            auth=owner.auth,
        )

        assert cancel_response.status_code == http_status.HTTP_200_OK
        payload = cancel_response.json['data']
        assert payload['status'] == WorkflowRun.STATUS_CANCELLED
        assert payload['business_key'].startswith(f'rdm:node:{node._id}')

        run = WorkflowRun.objects.get(id=run_id)
        assert run.status == WorkflowRun.STATUS_CANCELLED
        assert run.metadata['cancellations'][0]['reason'] == 'manual'

    def test_cancel_run_requires_admin_permissions(self):
        owner = AuthUserFactory()
        contributor = AuthUserFactory()
        node = self._create_project_with_workflow(owner)
        node.add_contributor(contributor, permissions='write')
        node.save()

        engine = self._create_engine(owner=owner)
        definition_id = 'restricted-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Restricted Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )

        start_response = self.app.post_json(
            self._run_url(node, template),
            {},
            auth=owner.auth,
        )
        run_id = int(start_response.json['data']['id'])

        forbidden = self.app.delete(
            self._run_detail_url(node, run_id),
            auth=contributor.auth,
            expect_errors=True,
        )

        assert forbidden.status_code == http_status.HTTP_403_FORBIDDEN

    def test_cancel_run_conflict_when_already_terminal(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'terminal-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Terminal Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )

        start_response = self.app.post_json(
            self._run_url(node, template),
            {},
            auth=owner.auth,
        )
        run_id = int(start_response.json['data']['id'])

        run = WorkflowRun.objects.get(id=run_id)
        run.status = WorkflowRun.STATUS_COMPLETED
        run.save(update_fields=['status'])

        conflict = self.app.delete(
            self._run_detail_url(node, run_id),
            auth=owner.auth,
            expect_errors=True,
        )

        assert conflict.status_code == http_status.HTTP_409_CONFLICT

    @mock.patch('addons.workflow.services.get_gateway_client')
    def test_list_tasks_returns_gateway_payload(self, mock_get_client):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'task-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='task-def-key',
            name='Task Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )
        activation = WorkflowActivation.objects.get(node=node, template=template)

        run = WorkflowRun.objects.create(
            node=node,
            template=template,
            activation=activation,
            engine=engine,
            started_by=owner,
            label='Task Run',
            business_key=f'rdm:node:{node._id}',
            engine_process_id='proc-123',
            engine_definition_id=definition_id,
        )

        client = mock.Mock()
        mock_get_client.return_value = client
        task_payload = {
            'id': 'task-1',
            'name': 'Fill Form',
            'processInstanceId': run.engine_process_id,
            'processInstanceBusinessKey': run.business_key,
            'processDefinitionId': definition_id,
            'createTime': '2025-01-01T00:00:00Z',
        }
        client.list_tasks.return_value = {'data': [task_payload]}

        response = self.app.get(self._tasks_url(node), auth=owner.auth)

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json['data']
        assert len(data) == 1
        assert data[0]['id'] == 'task-1'
        assert data[0]['run_id'] == run._id
        assert data[0]['engine_id'] == engine.engine_id

        client.list_tasks.assert_called_once()

    @mock.patch('addons.workflow.services.get_gateway_client')
    def test_retrieve_task_with_form(self, mock_get_client):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'detail-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='detail-def-key',
            name='Detail Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )
        activation = WorkflowActivation.objects.get(node=node, template=template)

        WorkflowRun.objects.create(
            node=node,
            template=template,
            activation=activation,
            engine=engine,
            started_by=owner,
            label='Detail Run',
            business_key=f'rdm:node:{node._id}',
            engine_process_id='proc-456',
            engine_definition_id=definition_id,
        )

        client = mock.Mock()
        mock_get_client.return_value = client
        client.get_task.return_value = {
            'id': 'task-2',
            'name': 'Review Submission',
            'processInstanceId': 'proc-456',
            'processInstanceBusinessKey': f'rdm:node:{node._id}',
            'processDefinitionId': definition_id,
        }
        client.get_task_form.return_value = {
            'key': 'review-form',
            'fields': [],
        }

        response = self.app.get(
            f"{self._task_detail_url(node, 'task-2')}?include_form=true",
            auth=owner.auth,
        )

        assert response.status_code == http_status.HTTP_200_OK
        payload = response.json['data']
        assert payload['id'] == 'task-2'
        assert payload['form']['key'] == 'review-form'
        client.get_task.assert_called_once_with('task-2')
        client.get_task_form.assert_called_once_with('task-2')

    @mock.patch('addons.workflow.services.get_gateway_client')
    def test_submit_task_action_completion_returns_no_content(self, mock_get_client):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'complete-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='complete-def-key',
            name='Complete Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )
        activation = WorkflowActivation.objects.get(node=node, template=template)

        WorkflowRun.objects.create(
            node=node,
            template=template,
            activation=activation,
            engine=engine,
            started_by=owner,
            label='Complete Run',
            business_key=f'rdm:node:{node._id}',
            engine_process_id='proc-789',
            engine_definition_id=definition_id,
        )

        client = mock.Mock()
        mock_get_client.return_value = client
        not_found_error = WorkflowGatewayClientError(
            http_status.HTTP_404_NOT_FOUND,
            'Not Found',
        )
        client.get_task.side_effect = [
            {
                'id': 'task-3',
                'name': 'Complete Task',
                'processInstanceId': 'proc-789',
                'processInstanceBusinessKey': f'rdm:node:{node._id}',
                'processDefinitionId': definition_id,
            },
            not_found_error,
        ]

        response = self.app.post_json(
            self._task_action_url(node, 'task-3'),
            {
                'action': 'complete',
                'variables': {'decision': 'approve'},
            },
            auth=owner.auth,
            status=http_status.HTTP_204_NO_CONTENT,
        )

        assert response.status_code == http_status.HTTP_204_NO_CONTENT
        client.update_task.assert_called_once()
        args, kwargs = client.update_task.call_args
        assert args[0] == 'task-3'
        assert args[1]['action'] == 'complete'
        assert {'name': 'decision', 'value': 'approve'} in args[1]['variables']

    def test_start_run_rejects_disabled_activation(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'disabled-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Disabled Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )
        activation = WorkflowActivation.objects.get(node=node, template=template)
        activation.is_enabled = False
        activation.save()

        response = self.app.post_json(
            self._run_url(node, template),
            {},
            auth=owner.auth,
            expect_errors=True,
        )

        assert response.status_code == http_status.HTTP_409_CONFLICT

    def test_start_run_rejects_non_dict_parameters(self):
        owner = AuthUserFactory()
        node = self._create_project_with_workflow(owner)

        engine = self._create_engine(owner=owner)
        definition_id = 'parameter-definition'
        WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id=definition_id,
            definition_key='process-def-key',
            name='Parameter Process',
            version=1,
        )

        self.app.post_json(
            self._template_url(node),
            {
                'engine_id': engine.engine_id,
                'definition_id': definition_id,
            },
            auth=owner.auth,
        )

        template = WorkflowTemplate.objects.get(
            node=node,
            definition__definition_id=definition_id,
        )

        response = self.app.post_json(
            self._run_url(node, template),
            {'parameters': 'not-a-dict'},
            auth=owner.auth,
            expect_errors=True,
        )

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
