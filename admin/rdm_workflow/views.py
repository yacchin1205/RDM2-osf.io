# -*- coding: utf-8 -*-

import logging
import uuid
from urllib.parse import urljoin

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from admin.rdm.utils import RdmPermissionMixin
from framework.exceptions import HTTPError

from addons.workflow.models import WorkflowEngine, WorkflowEngineKey
from addons.workflow.services import deactivate_workflow_engine, import_gateway_public_keys

from . import forms


logger = logging.getLogger(__name__)


class WorkflowEngineAdminMixin(RdmPermissionMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.is_super_admin or self.is_institutional_admin

    def get_engine_queryset(self):
        queryset = WorkflowEngine.objects.all().order_by('engine_id')
        if self.is_super_admin:
            return queryset
        return queryset.filter(created_by=self.request.user)

    def user_can_manage_engine(self, engine: WorkflowEngine) -> bool:
        if self.is_super_admin:
            return True
        return self.is_institutional_admin and engine.created_by_id == self.request.user.id


class WorkflowEngineListView(WorkflowEngineAdminMixin, TemplateView):
    template_name = 'rdm_workflow/engine_list.html'

    def get_context_data(self, **kwargs):
        context = super(WorkflowEngineListView, self).get_context_data(**kwargs)
        engines = self.get_engine_queryset()

        for engine in engines:
            engine.active_key_count = WorkflowEngineKey.objects.filter(
                engine_id=engine.engine_id,
                is_active=True
            ).count()

        context['engines'] = engines
        engine_form = kwargs.get('engine_form') or forms.WorkflowEngineForm()
        context['engine_form'] = engine_form
        context['is_super_admin'] = self.is_super_admin
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'create_engine':
            return self._handle_create(request)
        if action == 'deactivate_engine':
            return self._handle_deactivate(request)
        if action == 'activate_engine':
            return self._handle_activate(request)
        messages.error(request, _('Unsupported action requested.'))
        return redirect(reverse('rdm_workflow:engine-list'))

    def _handle_create(self, request):
        form = forms.WorkflowEngineForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(engine_form=form))

        engine = form.save(commit=False)
        engine.engine_id = str(uuid.uuid4())
        engine.created_by = request.user
        # Reuse the provided engine_claim_value if present, otherwise default lazily
        if not engine.engine_claim_value:
            engine.engine_claim_value = engine.engine_id
        engine.is_active = True
        engine.keyset_url = urljoin(engine.gateway_base_url.rstrip('/') + '/', 'keyset')
        try:
            engine.save()
        except Exception as error:
            form.add_error(None, _('Failed to register workflow engine: %(error)s') % {'error': error})
            return self.render_to_response(self.get_context_data(engine_form=form))

        imported_count = 0
        keyset_import_failed = False
        keyset_error_message = None
        try:
            imported_count = import_gateway_public_keys(engine)
        except HTTPError as error:
            keyset_import_failed = True
            detail = getattr(error, 'data', {})
            message = detail.get('message') if isinstance(detail, dict) else str(error)
            error_detail = detail.get('detail') if isinstance(detail, dict) else None

            parts = [message or _('Gateway keyset import failed')]
            if error_detail:
                parts.append(str(error_detail))
            keyset_error_message = '. '.join(parts)

            logger.warning(
                'Failed to import gateway keyset for engine %s: %s (detail: %s)',
                engine.engine_id,
                message,
                error_detail,
            )
        except Exception as exc:
            keyset_import_failed = True
            keyset_error_message = f'{type(exc).__name__}: {str(exc)}'
            logger.exception('Unexpected error while importing gateway keyset for engine %s', engine.engine_id)

        if imported_count:
            messages.success(
                request,
                _('Workflow engine "%(engine)s" was registered successfully and imported %(count)d public key(s) from the gateway.')
                % {'engine': engine.engine_id, 'count': imported_count},
            )
        elif keyset_import_failed:
            messages.error(
                request,
                _('Engine "%(engine)s" registered, but keyset import failed: %(error)s')
                % {'engine': engine.engine_id, 'error': keyset_error_message},
            )
        else:
            messages.success(
                request,
                _('Workflow engine "%(engine)s" was registered successfully.') % {'engine': engine.engine_id},
            )
        return redirect(reverse('rdm_workflow:engine-list'))

    def _handle_deactivate(self, request):
        engine_id = request.POST.get('engine_id')
        if not engine_id:
            messages.error(request, _('Engine identifier is required.'))
            return redirect(reverse('rdm_workflow:engine-list'))

        engine = get_object_or_404(WorkflowEngine, engine_id=engine_id)
        if not self.user_can_manage_engine(engine):
            raise PermissionDenied

        deactivate_workflow_engine(engine)

        messages.success(
            request,
            _('Workflow engine "%(engine)s" was deactivated.') % {'engine': engine.engine_id},
        )
        return redirect(reverse('rdm_workflow:engine-list'))

    def _handle_activate(self, request):
        engine_id = request.POST.get('engine_id')
        if not engine_id:
            messages.error(request, _('Engine identifier is required.'))
            return redirect(reverse('rdm_workflow:engine-list'))

        engine = get_object_or_404(WorkflowEngine, engine_id=engine_id)
        if not self.user_can_manage_engine(engine):
            raise PermissionDenied

        if engine.is_active:
            messages.info(
                request,
                _('Workflow engine "%(engine)s" is already active.') % {'engine': engine.engine_id},
            )
            return redirect(reverse('rdm_workflow:engine-list'))

        engine.is_active = True
        engine.save(update_fields=['is_active'])

        messages.success(
            request,
            _('Workflow engine "%(engine)s" was reactivated. Re-register or import keys before delegating workflows.')
            % {'engine': engine.engine_id},
        )
        return redirect(reverse('rdm_workflow:engine-list'))


class WorkflowEngineEditView(WorkflowEngineAdminMixin, TemplateView):
    template_name = 'rdm_workflow/engine_edit.html'

    def dispatch(self, request, *args, **kwargs):
        self.engine = get_object_or_404(WorkflowEngine, engine_id=kwargs.get('engine_id'))
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        if not super().test_func():
            return False
        return self.user_can_manage_engine(self.engine)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['engine'] = self.engine
        engine_form = kwargs.get('engine_form') or forms.WorkflowEngineForm(instance=self.engine)
        context['engine_form'] = engine_form
        context['is_super_admin'] = self.is_super_admin
        return context

    def post(self, request, *args, **kwargs):
        form = forms.WorkflowEngineForm(request.POST, instance=self.engine)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(engine_form=form))

        form.save()
        messages.success(
            request,
            _('Workflow engine "%(engine)s" was updated successfully.') % {'engine': self.engine.engine_id},
        )
        return redirect(reverse('rdm_workflow:engine-list'))


class WorkflowEngineKeyView(WorkflowEngineAdminMixin, TemplateView):
    template_name = 'rdm_workflow/engine_keys.html'

    def dispatch(self, request, *args, **kwargs):
        self.engine = get_object_or_404(WorkflowEngine, engine_id=kwargs.get('engine_id'))
        return super(WorkflowEngineKeyView, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        # Ensure parent mixin checks super/admin status first
        if not super(WorkflowEngineKeyView, self).test_func():
            return False
        return self.user_can_manage_engine(self.engine)

    def get_context_data(self, **kwargs):
        context = super(WorkflowEngineKeyView, self).get_context_data(**kwargs)
        context['engine'] = self.engine
        context['keys'] = WorkflowEngineKey.objects.filter(engine_id=self.engine.engine_id).order_by('kid')
        key_form = kwargs.get('key_form') or forms.WorkflowEngineKeyForm()
        context['key_form'] = key_form
        context['is_super_admin'] = self.is_super_admin
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'add_key':
            return self._handle_add_key(request)
        if action == 'deactivate_key':
            return self._handle_deactivate_key(request)
        if action == 'import_keyset':
            return self._handle_import_keyset(request)
        messages.error(request, _('Unsupported action requested.'))
        return redirect(self._current_url())

    def _handle_add_key(self, request):
        form = forms.WorkflowEngineKeyForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(key_form=form))

        data = form.cleaned_data
        with transaction.atomic():
            WorkflowEngineKey.objects.update_or_create(
                engine_id=self.engine.engine_id,
                kid=data['kid'],
                defaults={
                    'algorithm': data['algorithm'],
                    'public_key': data['public_key'],
                    'is_active': True,
                },
            )

        messages.success(
            request,
            _('Public key "%(kid)s" was registered for engine %(engine)s.')
            % {'kid': data['kid'], 'engine': self.engine.engine_id},
        )
        return redirect(self._current_url())

    def _handle_deactivate_key(self, request):
        kid = request.POST.get('kid')
        if not kid:
            messages.error(request, _('Key identifier is required.'))
            return redirect(self._current_url())

        updated = WorkflowEngineKey.objects.filter(engine_id=self.engine.engine_id, kid=kid).update(is_active=False)
        if updated:
            messages.success(
                request,
                _('Public key "%(kid)s" was deactivated.') % {'kid': kid},
            )
        else:
            messages.warning(
                request,
                _('No matching active key was found to deactivate.'),
            )
        return redirect(self._current_url())

    def _handle_import_keyset(self, request):
        try:
            imported_count = import_gateway_public_keys(self.engine)
            messages.success(
                request,
                _('Successfully imported %(count)d public key(s) from the gateway.') % {'count': imported_count},
            )
        except HTTPError as error:
            detail = getattr(error, 'data', {})
            message = detail.get('message') if isinstance(detail, dict) else str(error)
            error_detail = detail.get('detail') if isinstance(detail, dict) else None

            parts = [message or _('Gateway keyset import failed')]
            if error_detail:
                parts.append(str(error_detail))
            full_error = '. '.join(parts)

            logger.warning(
                'Failed to import gateway keyset for engine %s: %s (detail: %s)',
                self.engine.engine_id,
                message,
                error_detail,
            )
            messages.error(
                request,
                _('Keyset import failed: %(error)s')
                % {'error': full_error},
            )
        except Exception as exc:
            logger.exception('Unexpected error while importing gateway keyset for engine %s', self.engine.engine_id)
            messages.error(
                request,
                _('Keyset import encountered an unexpected error: %(error)s')
                % {'error': f'{type(exc).__name__}: {str(exc)}'},
            )
        return redirect(self._current_url())

    def _current_url(self):
        return reverse('rdm_workflow:engine-keys', kwargs={'engine_id': self.engine.engine_id})
