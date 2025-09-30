# -*- coding: utf-8 -*-
"""Unit tests for workflow addon node settings."""

import uuid

import pytest

from framework.auth.core import Auth

from osf_tests.factories import AuthUserFactory, ProjectFactory

from addons.workflow.models import (
    NodeSettings,
    WorkflowActivation,
    WorkflowDefinitionSnapshot,
    WorkflowEngine,
    WorkflowRegistration,
)
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db


class WorkflowNodeSettingsTests(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.node = ProjectFactory(creator=self.user)
        self.node.add_addon('workflow', auth=self.auth)
        self.node_settings = self.node.get_addon('workflow')
        assert isinstance(self.node_settings, NodeSettings)

    def test_complete_always_true(self):
        assert self.node_settings.complete is True

    def test_active_registrations_empty_without_entries(self):
        assert list(self.node_settings.active_registrations) == []

    def test_active_registrations_filters_inactive(self):
        engine = WorkflowEngine.objects.create(
            engine_id=str(uuid.uuid4()),
            gateway_base_url='https://workflow.example/api/',
            signing_kid='kid-test',
        )
        snapshot_active = WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id='definition-active',
            definition_key='definition-active',
            name='Active Process',
            version=1,
        )
        snapshot_inactive = WorkflowDefinitionSnapshot.objects.create(
            engine=engine,
            definition_id='definition-inactive',
            definition_key='definition-inactive',
            name='Inactive Process',
            version=1,
        )

        active_registration = WorkflowRegistration.objects.create(
            node=self.node,
            definition=snapshot_active,
            registered_by=self.user,
        )
        inactive_registration = WorkflowRegistration.objects.create(
            node=self.node,
            definition=snapshot_inactive,
            registered_by=self.user,
            is_active=False,
        )

        WorkflowActivation.objects.create(
            node=self.node,
            registration=active_registration,
            activated_by=self.user,
            is_enabled=True,
        )
        WorkflowActivation.objects.create(
            node=self.node,
            registration=inactive_registration,
            activated_by=self.user,
            is_enabled=False,
        )

        registrations = list(self.node_settings.active_registrations)
        assert registrations == [active_registration]
