'use strict';

const $ = require('jquery');
const ko = require('knockout');
const Raven = require('raven-js');

const $osf = require('js/osfHelpers');
const ChangeMessageMixin = require('js/changeMessage');
const _ = require('js/rdmGettext')._;

function formatTokenMode(mode) {
    if (mode === 'readwrite') return 'RW';
    if (mode === 'read') return 'R';
    return '-';
}

function formatTokenSettings(tokenSettings) {
    if (!tokenSettings) return '';
    const parts = [];
    if (tokenSettings.creator_mode && tokenSettings.creator_mode !== 'none') {
        parts.push('Creator:' + formatTokenMode(tokenSettings.creator_mode));
    }
    if (tokenSettings.manager_mode && tokenSettings.manager_mode !== 'none') {
        parts.push('Manager:' + formatTokenMode(tokenSettings.manager_mode));
    }
    if (tokenSettings.executor_mode && tokenSettings.executor_mode !== 'none') {
        parts.push('Executor:' + formatTokenMode(tokenSettings.executor_mode));
    }
    return parts.length ? '🔑 ' + parts.join(' ') : '';
}

function WorkflowRegistration(data) {
    const self = this;
    self.id = data.id;
    self.node_id = data.node_id;
    self.node_title = data.node_title;
    self.engine_id = data.engine_id;
    self.definition_id = data.definition_id;
    self.definition_key = data.definition_key;
    self.definition_name = data.definition_name;
    self.definition_version = data.definition_version;
    self.definition_description = data.definition_description;
    self.definition_deployment_id = data.definition_deployment_id;
    self.label = ko.observable(data.label || '');
    self.description = ko.observable(data.description || '');
    self.isLocal = data.is_local === true;
    self.isActive = ko.observable(data.is_active === true);
    self.isEnabled = ko.observable(data.is_enabled === true);
    self.activationId = data.activation_id || null;
    self.token_settings = ko.observable(data.token_settings);
    self.tokenSettingsDisplay = ko.pureComputed(function() {
        return formatTokenSettings(self.token_settings());
    });

    self.nodeUrl = self.node_id ? '/' + self.node_id + '/' : null;
    self.localizedScopeLabel = _('This project');
    self.sharedScopeLabel = _('Shared project');
    self.enabledLabel = _('Enabled');
    self.disabledLabel = _('Disabled');
    self.enableLabel = _('Enable');
    self.disableLabel = _('Disable');
    self.activeLabel = _('Active');
    self.inactiveLabel = _('Inactive');
}

WorkflowRegistration.prototype.updateFrom = function(payload) {
    this.label(payload.label || '');
    this.description(payload.description || '');
    this.isActive(payload.is_active === true);
    this.isEnabled(payload.is_enabled === true);
    this.node_id = payload.node_id;
    this.node_title = payload.node_title;
    this.nodeUrl = this.node_id ? '/' + this.node_id + '/' : null;
    this.definition_id = payload.definition_id;
    this.definition_key = payload.definition_key;
    this.definition_name = payload.definition_name;
    this.definition_version = payload.definition_version;
    this.definition_description = payload.definition_description;
    this.definition_deployment_id = payload.definition_deployment_id;
    this.activationId = payload.activation_id || null;
    this.token_settings(payload.token_settings);
};

function WorkflowActivation(data, registration) {
    const self = this;
    self.id = data.activation_id;
    self.registration_id = data.id;
    self.registration = registration;
    self.label = registration.label();
    self.description = registration.description();
    self.definition_name = registration.definition_name;
    self.definition_id = registration.definition_id;
    self.engine_id = registration.engine_id;
    self.node_title = registration.node_title;
    self.nodeUrl = registration.nodeUrl;
    self.isLocal = registration.isLocal;
    self.disableLabel = _('Disable');
}

function WorkflowNodeSettingsViewModel(options) {
    const self = this;
    ChangeMessageMixin.call(self);

    self.nodeId = options.nodeId;
    self.registrationsUrl = options.registrationsUrl;
    self.enginesUrl = options.enginesUrl || '/api/v1/workflow/engines/';

    self.registrations = ko.observableArray([]);
    self.activations = ko.observableArray([]);
    self.isLoading = ko.observable(true);
    self.loadError = ko.observable('');
    self.isRefreshing = ko.observable(false);
    self.isSubmitting = ko.observable(false);

    self.isLoadingEngines = ko.observable(true);
    self.engineLoadError = ko.observable('');
    self.engines = ko.observableArray([]);
    self.selectEngineCaption = _('Select an engine…');

    self.isLoadingDefinitions = ko.observable(false);
    self.definitionLoadError = ko.observable('');
    self.definitions = ko.observableArray([]);
    self.selectDefinitionCaption = _('Select a definition…');
    self.selectedDefinitionId = ko.observable('');

    self.errors = ko.observable({});
    self.togglingIds = ko.observableArray([]);
    self.deletingIds = ko.observableArray([]);

    self.tokenPermissionRequest = {
        creatorMode: ko.observable('none'),
        creatorModeLabel: ko.pureComputed(function() {
            const mode = self.tokenPermissionRequest.creatorMode();
            if (mode === 'readwrite') return _('ReadWrite permission: Full access to read and modify resources');
            if (mode === 'read') return _('Read permission: Read-only access to resources');
            return '';
        }),
        pendingPayload: null,
    };

    self.enableTokenRequest = {
        creatorMode: ko.observable('none'),
        creatorModeLabel: ko.pureComputed(function() {
            const mode = self.enableTokenRequest.creatorMode();
            if (mode === 'readwrite') return _('ReadWrite permission: Full access to read and modify resources');
            if (mode === 'read') return _('Read permission: Read-only access to resources');
            return '';
        }),
        pendingRegistration: null,
    };

    self.registrationEnableTokenRequest = {
        creatorMode: ko.observable('none'),
        creatorModeLabel: ko.pureComputed(function() {
            const mode = self.registrationEnableTokenRequest.creatorMode();
            if (mode === 'readwrite') return _('ReadWrite permission: Full access to read and modify resources');
            if (mode === 'read') return _('Read permission: Read-only access to resources');
            return '';
        }),
        pendingRegistration: null,
    };

    self.activateTokenRequest = {
        managerMode: ko.observable('none'),
        managerModeLabel: ko.pureComputed(function() {
            const mode = self.activateTokenRequest.managerMode();
            if (mode === 'readwrite') return _('ReadWrite permission: Full access to read and modify resources');
            if (mode === 'read') return _('Read permission: Read-only access to resources');
            return '';
        }),
        pendingRegistrationId: null,
    };

    self.deleteRegistrationRequest = {
        pendingRegistration: ko.observable(null),
    };

    self.form = {
        engineId: ko.observable(''),
        definitionSource: ko.observable('existing'),
        definitionId: ko.observable(''),
        selectedFile: ko.observable(null),
        label: ko.observable(''),
        description: ko.observable(''),
        creatorTokenMode: ko.observable('none'),
        managerTokenMode: ko.observable('none'),
        executorTokenMode: ko.observable('none'),
    };

    self.activateForm = {
        selectedRegistrationId: ko.observable(''),
    };

    self.hasEngines = ko.computed(function() {
        return self.engines().length > 0;
    });

    self.hasDefinitions = ko.computed(function() {
        return self.definitions().length > 0;
    });

    self.canUploadWorkflowZip = ko.computed(function() {
        const engineId = self.form.engineId();
        if (!engineId) {
            return false;
        }
        const engine = self.engines().find(function(e) {
            return e.engine_id === engineId;
        });
        return engine && engine.allow_upload;
    });

    self.localRegistrations = ko.computed(function() {
        return self.registrations().filter(function(reg) {
            return reg.isLocal === true;
        });
    });

    self.availableRegistrationsForActivation = ko.computed(function() {
        const activatedIds = self.activations().map(function(act) {
            return act.registration_id;
        });
        return self.registrations().filter(function(reg) {
            return reg.isActive() && activatedIds.indexOf(reg.id) === -1;
        });
    });

    self.isToggling = function(registrationId) {
        return self.togglingIds().indexOf(registrationId) !== -1;
    };

    self.isDeleting = function(registrationId) {
        return self.deletingIds().indexOf(registrationId) !== -1;
    };

    self.form.engineId.subscribe(function(engineId) {
        const current = $.extend({}, self.errors());
        if (current.engineId) {
            delete current.engineId;
            self.errors(current);
        }
        self.loadDefinitions(engineId);
    });

    self.form.definitionId.subscribe(function() {
        const current = $.extend({}, self.errors());
        if (current.definitionId) {
            delete current.definitionId;
            self.errors(current);
        }
    });

    self.selectedDefinitionId.subscribe(function(value) {
        self.form.definitionId(value || '');
        const current = $.extend({}, self.errors());
        if (current.definitionId) {
            delete current.definitionId;
            self.errors(current);
        }
    });

    self.refreshDefinitions = function() {
        const engineId = self.form.engineId();
        if (engineId) {
            self.loadDefinitions(engineId);
        }
    };

    self.handleFileSelect = function(_context, event) {
        const files = event.target.files;
        if (files && files.length > 0) {
            self.form.selectedFile(files[0]);
            const current = $.extend({}, self.errors());
            if (current.workflowZip) {
                delete current.workflowZip;
                self.errors(current);
            }
        }
    };

    self.formatFileSize = function(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    };

    self.fetchEngines = function() {
        self.engineLoadError('');
        self.isLoadingEngines(true);
        return $.ajax({
            url: self.enginesUrl,
            type: 'GET',
            dataType: 'json',
        }).done(function(response) {
            const data = response && response.data ? response.data : [];
            const activeEngines = data.filter(function(entry) {
                return entry && entry.is_active === true;
            });
            activeEngines.forEach(function(entry) {
                entry.display = entry.engine_id + (entry.gateway_base_url ? ' (' + entry.gateway_base_url + ')' : '');
            });
            activeEngines.sort(function(a, b) {
                return a.display.localeCompare(b.display);
            });
            self.engines(activeEngines);
            if (!activeEngines.length) {
                if (data.length) {
                    self.engineLoadError(_('No active workflow engines are available for this project.'));
                } else {
                    self.engineLoadError(_('No workflow engines are registered yet.'));
                }
            }
            if (activeEngines.length === 1) {
                self.form.engineId(activeEngines[0].engine_id);
            }
        }).fail(function(xhr, textStatus, error) {
            const message = _('Could not load available workflow engines.');
            self.engineLoadError(message);
            Raven.captureMessage('Failed to load workflow engines', {
                extra: {
                    url: self.enginesUrl,
                    textStatus: textStatus,
                    error: error,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.isLoadingEngines(false);
        });
    };

    self.loadDefinitions = function(engineId) {
        self.definitionLoadError('');
        self.isLoadingDefinitions(false);
        self.definitions([]);
        self.selectedDefinitionId('');
        self.form.definitionId('');

        if (!engineId) {
                return;
        }

        self.isLoadingDefinitions(true);

        return $.ajax({
            url: self.enginesUrl + encodeURIComponent(engineId) + '/definitions/',
            type: 'GET',
            dataType: 'json',
            data: { size: 200, latest: 'true' },
        }).done(function(response) {
            const data = response && response.data ? response.data : [];
            const mapped = data.map(function(entry) {
                const definitionId = entry.definition_id || entry.id;
                const name = entry.definition_name || entry.name || definitionId;
                const key = entry.definition_key || entry.key;
                const version = entry.definition_version || entry.version;
                let display = name;
                if (version) {
                    display += ' (v' + version + ')';
                }
                if (key && key !== name) {
                    display += ' – ' + key;
                }
                display += ' [' + definitionId + ']';
                return {
                    definition_id: definitionId,
                    definition_key: key,
                    display: display,
                    raw: entry,
                };
            }).sort(function(a, b) {
                return a.display.localeCompare(b.display);
            });

            self.definitions(mapped);
            if (!mapped.length) {
                self.selectedDefinitionId('');
                self.form.definitionId('');
            }
        }).fail(function(xhr, textStatus, error) {
            const message = _('Could not load workflow definitions.');
            self.definitionLoadError(message);
            Raven.captureMessage('Failed to load workflow definitions', {
                extra: {
                    url: self.enginesUrl + encodeURIComponent(engineId) + '/definitions/',
                    textStatus: textStatus,
                    error: error,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.isLoadingDefinitions(false);
        });
    };

    self.fetchRegistrations = function() {
        self.loadError('');
        if (self.registrations().length) {
            self.isRefreshing(true);
        }

        const selectedEngineId = self.form.engineId();

        self.fetchEngines();
        if (selectedEngineId) {
            self.loadDefinitions(selectedEngineId);
        }

        return $.ajax({
            url: self.registrationsUrl,
            type: 'GET',
            dataType: 'json',
        }).done(function(response) {
            const data = response && response.data ? response.data : [];
            const existing = {};
            self.registrations().forEach(function(reg) {
                existing[reg.id] = reg;
            });
            const mapped = data.map(function(entry) {
                if (existing[entry.id]) {
                    existing[entry.id].updateFrom(entry);
                    existing[entry.id].isLocal = entry.is_local === true;
                    existing[entry.id].engine_id = entry.engine_id;
                    return existing[entry.id];
                }
                return new WorkflowRegistration(entry);
            });
            mapped.sort(function(a, b) {
                if (a.isLocal !== b.isLocal) {
                    return a.isLocal ? -1 : 1;
                }
                const aLabel = (a.label && a.label()) || a.definition_name || a.definition_id || '';
                const bLabel = (b.label && b.label()) || b.definition_name || b.definition_id || '';
                return aLabel.localeCompare(bLabel);
            });
            self.registrations(mapped);

            const activations = [];
            const registrationMap = {};
            mapped.forEach(function(reg) {
                registrationMap[reg.id] = reg;
            });
            data.forEach(function(entry) {
                if (entry.activation_id && entry.is_enabled) {
                    const reg = registrationMap[entry.id];
                    if (reg) {
                        activations.push(new WorkflowActivation(entry, reg));
                    }
                }
            });
            activations.sort(function(a, b) {
                if (a.isLocal !== b.isLocal) {
                    return a.isLocal ? -1 : 1;
                }
                return a.label.localeCompare(b.label);
            });
            self.activations(activations);
        }).fail(function(xhr, textStatus, error) {
            const message = _('Could not load workflow registrations.');
            self.loadError(message);
            self.changeMessage(message, 'text-danger');
            Raven.captureMessage('Failed to load workflow registrations', {
                extra: {
                    url: self.registrationsUrl,
                    textStatus: textStatus,
                    error: error,
                },
            });
        }).always(function() {
            self.isLoading(false);
            self.isRefreshing(false);
        });
    };

    self.resetForm = function() {
        self.form.engineId('');
        self.form.definitionSource('existing');
        self.form.definitionId('');
        self.form.selectedFile(null);
        self.form.label('');
        self.form.description('');
        self.form.creatorTokenMode('none');
        self.form.managerTokenMode('none');
        self.form.executorTokenMode('none');
        self.errors({});
        self.definitionLoadError('');
        self.definitions([]);
        self.selectedDefinitionId('');
        const fileInput = document.getElementById('workflow-zip');
        if (fileInput) {
            fileInput.value = '';
        }
    };

    self.submitRegistration = function(_context, event) {
        if (event && typeof event.preventDefault === 'function') {
            event.preventDefault();
        }
        if (self.isSubmitting()) {
            return false;
        }

        const errors = {};
        const engineId = (self.form.engineId() || '').trim();
        const definitionSource = self.form.definitionSource();

        console.log('submitRegistration: definitionSource =', definitionSource);
        console.log('submitRegistration: selectedFile =', self.form.selectedFile());

        if (!engineId) {
            errors.engineId = _('Engine selection is required.');
        }

        if (definitionSource === 'existing') {
            const definitionId = (self.selectedDefinitionId() || '').trim();
            self.form.definitionId(definitionId);

            if (!definitionId) {
                errors.definitionId = _('Definition ID is required.');
            }
        } else if (definitionSource === 'upload') {
            if (!self.form.selectedFile()) {
                errors.workflowZip = _('Workflow ZIP file is required.');
            }
        }

        if (Object.keys(errors).length) {
            self.errors(errors);
            return false;
        }

        self.errors({});

        const creatorMode = self.form.creatorTokenMode();
        const tokenSettings = {
            creator_mode: creatorMode,
            manager_mode: self.form.managerTokenMode(),
            executor_mode: self.form.executorTokenMode(),
        };

        if (creatorMode !== 'none') {
            self.tokenPermissionRequest.creatorMode(creatorMode);
            self.tokenPermissionRequest.pendingPayload = {
                engineId: engineId,
                definitionSource: definitionSource,
                selectedFile: self.form.selectedFile(),
                label: (self.form.label() || '').trim(),
                description: (self.form.description() || '').trim(),
                definitionId: self.form.definitionId(),
                tokenSettings: tokenSettings,
            };
            $('#tokenPermissionModal').modal('show');
            return false;
        }

        self.isSubmitting(true);

        let requestPromise;
        console.log('Checking definitionSource:', definitionSource, typeof definitionSource);
        console.log('Comparison result:', definitionSource === 'upload');
        if (definitionSource === 'upload') {
            console.log('BRANCH: upload - creating FormData');
            const formData = new FormData();
            formData.append('workflow_zip', self.form.selectedFile());
            formData.append('engine_id', engineId);
            console.log('FormData created');
            const label = (self.form.label() || '').trim();
            if (label) {
                formData.append('label', label);
            }
            const description = (self.form.description() || '').trim();
            if (description) {
                formData.append('description', description);
            }
            formData.append('token_settings', JSON.stringify(tokenSettings));

            console.log('About to call with formData:', formData);

            const actualFormData = formData.fd || formData;
            console.log('Using actualFormData:', actualFormData);

            const deferred = $.Deferred();

            fetch(self.registrationsUrl, {
                method: 'POST',
                body: actualFormData,
                credentials: 'same-origin'
            }).then(function(response) {
                if (!response.ok) {
                    return response.json().then(function(data) {
                        deferred.reject({ status: response.status, responseJSON: data });
                    }).catch(function() {
                        deferred.reject({ status: response.status, responseJSON: { message: response.statusText } });
                    });
                } else {
                    return response.json().then(function(data) {
                        deferred.resolve(data);
                    });
                }
            }).catch(function(error) {
                deferred.reject({ status: 0, responseJSON: { message: error.message } });
            });

            requestPromise = deferred.promise();
            console.log('Fetch called, requestPromise =', requestPromise);
        } else {
            console.log('BRANCH: existing - creating JSON payload');
            const payload = {
                engine_id: engineId,
                definition_id: self.form.definitionId(),
            };
            const label = (self.form.label() || '').trim();
            if (label) {
                payload.label = label;
            }
            const description = (self.form.description() || '').trim();
            if (description) {
                payload.description = description;
            }
            payload.token_settings = tokenSettings;

            requestPromise = $osf.postJSON(self.registrationsUrl, payload);
        }

        return requestPromise
            .done(function(response) {
                const data = response && response.data;
                if (!data) {
                    self.changeMessage(_('Workflow registration created.'), 'text-success');
                    self.fetchRegistrations();
                } else {
                    const existing = self.registrations().find(function(item) {
                        return item.id === data.id;
                    });
                    if (existing) {
                        existing.updateFrom(data);
                        existing.isLocal = data.is_local === true;
                    } else {
                        self.registrations.push(new WorkflowRegistration(data));
                    }
                    const created = response && response.created;
                    const message = created ? _('Workflow registration created.') : _('Workflow registration updated.');
                    self.changeMessage(message, 'text-success');
                }
                self.resetForm();
            })
            .fail(function(xhr) {
                const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
                const message = detail || _('Failed to register workflow.');
                const current = $.extend({}, self.errors());
                if (detail) {
                    if (definitionSource === 'upload') {
                        current.workflowZip = detail;
                    } else {
                        current.definitionId = detail;
                    }
                }
                self.errors(current);
                self.changeMessage(message, 'text-danger');
                Raven.captureMessage('Failed to register workflow', {
                    extra: {
                        url: self.registrationsUrl,
                        response: xhr && xhr.responseJSON,
                    },
                });
            })
            .always(function() {
                self.isSubmitting(false);
            });
    };

    self.confirmTokenPermission = function() {
        $('#tokenPermissionModal').modal('hide');
        const payload = self.tokenPermissionRequest.pendingPayload;
        console.log('confirmTokenPermission: payload =', payload);
        if (!payload) {
            return;
        }
        self.tokenPermissionRequest.pendingPayload = null;
        self.isSubmitting(true);

        console.log('confirmTokenPermission: definitionSource =', payload.definitionSource);
        console.log('confirmTokenPermission: selectedFile =', payload.selectedFile);

        let requestPromise;
        if (payload.definitionSource === 'upload') {
            const formData = new FormData();
            formData.append('workflow_zip', payload.selectedFile);
            formData.append('engine_id', payload.engineId);
            if (payload.label) {
                formData.append('label', payload.label);
            }
            if (payload.description) {
                formData.append('description', payload.description);
            }
            formData.append('token_settings', JSON.stringify(payload.tokenSettings));

            const actualFormData = formData.fd || formData;

            const deferred = $.Deferred();

            fetch(self.registrationsUrl, {
                method: 'POST',
                body: actualFormData,
                credentials: 'same-origin'
            }).then(function(response) {
                if (!response.ok) {
                    return response.json().then(function(data) {
                        deferred.reject({ status: response.status, responseJSON: data });
                    }).catch(function() {
                        deferred.reject({ status: response.status, responseJSON: { message: response.statusText } });
                    });
                } else {
                    return response.json().then(function(data) {
                        deferred.resolve(data);
                    });
                }
            }).catch(function(error) {
                deferred.reject({ status: 0, responseJSON: { message: error.message } });
            });

            requestPromise = deferred.promise();
        } else {
            const jsonPayload = {
                engine_id: payload.engineId,
                definition_id: payload.definitionId,
            };
            if (payload.label) {
                jsonPayload.label = payload.label;
            }
            if (payload.description) {
                jsonPayload.description = payload.description;
            }
            jsonPayload.token_settings = payload.tokenSettings;

            requestPromise = $osf.postJSON(self.registrationsUrl, jsonPayload);
        }

        return requestPromise
            .done(function(response) {
                const data = response && response.data;
                if (!data) {
                    self.changeMessage(_('Workflow registration created.'), 'text-success');
                    self.fetchRegistrations();
                } else {
                    const existing = self.registrations().find(function(item) {
                        return item.id === data.id;
                    });
                    if (existing) {
                        existing.updateFrom(data);
                        existing.isLocal = data.is_local === true;
                    } else {
                        self.registrations.push(new WorkflowRegistration(data));
                    }
                    const created = response && response.created;
                    const message = created ? _('Workflow registration created.') : _('Workflow registration updated.');
                    self.changeMessage(message, 'text-success');
                }
                self.resetForm();
            })
            .fail(function(xhr) {
                const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
                const message = detail || _('Failed to register workflow.');
                const current = $.extend({}, self.errors());
                if (detail) {
                    current.definitionId = detail;
                }
                self.errors(current);
                self.changeMessage(message, 'text-danger');
                Raven.captureMessage('Failed to register workflow', {
                    extra: {
                        url: self.registrationsUrl,
                        response: xhr && xhr.responseJSON,
                    },
                });
            })
            .always(function() {
                self.isSubmitting(false);
            });
    };

    self.activateWorkflow = function() {
        const registrationId = self.activateForm.selectedRegistrationId();
        if (!registrationId) {
            return;
        }

        const registration = self.registrations().find(function(reg) {
            return reg.id === registrationId;
        });
        if (!registration) {
            return;
        }

        const managerMode = registration.token_settings().manager_mode;
        if (managerMode && managerMode !== 'none') {
            self.activateTokenRequest.managerMode(managerMode);
            self.activateTokenRequest.pendingRegistrationId = registrationId;
            $('#activateTokenPermissionModal').modal('show');
            return;
        }

        const url = self.registrationsUrl + registrationId + '/activation/';
        self.isSubmitting(true);
        return $osf.putJSON(url, {
            is_enabled: true,
        }).done(function(response) {
            self.fetchRegistrations().done(function() {
                self.activateForm.selectedRegistrationId('');
                self.changeMessage(_('Workflow activated.'), 'text-success');
            });
        }).fail(function(xhr) {
            const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
            const message = detail || _('Failed to activate workflow.');
            self.changeMessage(message, 'text-danger');
            $osf.growl('Error', message);
            Raven.captureMessage('Failed to activate workflow', {
                extra: {
                    url: url,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.isSubmitting(false);
        });
    };

    self.confirmActivateToken = function() {
        $('#activateTokenPermissionModal').modal('hide');
        const registrationId = self.activateTokenRequest.pendingRegistrationId;
        if (!registrationId) {
            return;
        }
        self.activateTokenRequest.pendingRegistrationId = null;

        const url = self.registrationsUrl + registrationId + '/activation/';
        self.isSubmitting(true);
        return $osf.putJSON(url, {
            is_enabled: true,
        }).done(function(response) {
            self.fetchRegistrations().done(function() {
                self.activateForm.selectedRegistrationId('');
                self.changeMessage(_('Workflow activated.'), 'text-success');
            });
        }).fail(function(xhr) {
            const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
            const message = detail || _('Failed to activate workflow.');
            self.changeMessage(message, 'text-danger');
            $osf.growl('Error', message);
            Raven.captureMessage('Failed to activate workflow', {
                extra: {
                    url: url,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.isSubmitting(false);
        });
    };

    self.deactivateWorkflow = function(activation) {
        const url = self.registrationsUrl + activation.registration_id + '/activation/';
        self.togglingIds.push(activation.id);
        return $osf.putJSON(url, {
            is_enabled: false,
        }).done(function() {
            self.fetchRegistrations().done(function() {
                self.changeMessage(_('Workflow deactivated.'), 'text-success');
            });
        }).fail(function(xhr) {
            const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
            const message = detail || _('Failed to deactivate workflow.');
            self.changeMessage(message, 'text-danger');
            $osf.growl('Error', message);
            Raven.captureMessage('Failed to deactivate workflow', {
                extra: {
                    url: url,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.togglingIds.remove(activation.id);
        });
    };

    self.toggleRegistrationActive = function(registration) {
        if (self.isToggling(registration.id)) {
            return;
        }
        const newActiveState = !registration.isActive();

        if (newActiveState) {
            const creatorMode = registration.token_settings().creator_mode;
            if (creatorMode && creatorMode !== 'none') {
                self.registrationEnableTokenRequest.creatorMode(creatorMode);
                self.registrationEnableTokenRequest.pendingRegistration = registration;
                $('#registrationEnableTokenPermissionModal').modal('show');
                return;
            }
        }

        const url = self.registrationsUrl + registration.id + '/';
        self.togglingIds.push(registration.id);

        return $.ajax({
            url: url,
            type: 'PATCH',
            contentType: 'application/json',
            data: JSON.stringify({
                is_active: newActiveState,
            }),
        }).done(function(response) {
            const data = response && response.data;
            if (data) {
                registration.isActive(data.is_active === true);
                self.changeMessage(
                    newActiveState ? _('Workflow registration enabled.') : _('Workflow registration disabled.'),
                    'text-success'
                );
            }
        }).fail(function(xhr) {
            const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
            const message = detail || _('Failed to update workflow registration.');
            self.changeMessage(message, 'text-danger');
            $osf.growl('Error', message);
            Raven.captureMessage('Failed to update workflow registration', {
                extra: {
                    url: url,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.togglingIds.remove(registration.id);
        });
    };

    self.deleteRegistration = function(registration) {
        if (self.isDeleting(registration.id)) {
            return;
        }

        self.deleteRegistrationRequest.pendingRegistration(registration);
        $('#deleteRegistrationModal').modal('show');
    };

    self.confirmDeleteRegistration = function() {
        $('#deleteRegistrationModal').modal('hide');
        const registration = self.deleteRegistrationRequest.pendingRegistration();
        if (!registration) {
            return;
        }
        self.deleteRegistrationRequest.pendingRegistration(null);

        const url = self.registrationsUrl + registration.id + '/';
        self.deletingIds.push(registration.id);

        return $.ajax({
            url: url,
            type: 'DELETE',
        }).done(function() {
            self.registrations.remove(registration);
            self.changeMessage(_('Workflow registration deleted.'), 'text-success');
        }).fail(function(xhr) {
            const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
            const message = detail || _('Failed to delete workflow registration.');
            self.changeMessage(message, 'text-danger');
            $osf.growl('Error', message);
            Raven.captureMessage('Failed to delete workflow registration', {
                extra: {
                    url: url,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.deletingIds.remove(registration.id);
        });
    };

    self.confirmRegistrationEnableToken = function() {
        $('#registrationEnableTokenPermissionModal').modal('hide');
        const registration = self.registrationEnableTokenRequest.pendingRegistration;
        if (!registration) {
            return;
        }
        self.registrationEnableTokenRequest.pendingRegistration = null;

        const url = self.registrationsUrl + registration.id + '/';
        self.togglingIds.push(registration.id);
        return $.ajax({
            url: url,
            type: 'PATCH',
            contentType: 'application/json',
            data: JSON.stringify({
                is_active: true,
            }),
        }).done(function(response) {
            const data = response && response.data;
            if (data) {
                registration.isActive(data.is_active === true);
                self.changeMessage(_('Workflow registration enabled.'), 'text-success');
            }
        }).fail(function(xhr) {
            const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
            const message = detail || _('Failed to update workflow registration.');
            self.changeMessage(message, 'text-danger');
            $osf.growl('Error', message);
            Raven.captureMessage('Failed to update workflow registration', {
                extra: {
                    url: url,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.togglingIds.remove(registration.id);
        });
    };

    self.confirmEnableToken = function() {
        $('#enableTokenPermissionModal').modal('hide');
        const registration = self.enableTokenRequest.pendingRegistration;
        if (!registration) {
            return;
        }
        self.enableTokenRequest.pendingRegistration = null;

        const url = self.registrationsUrl + registration.id + '/activation/';
        self.togglingIds.push(registration.id);
        return $osf.putJSON(url, {
            is_enabled: true,
        }).done(function(response) {
            const data = response && response.data;
            if (data) {
                registration.isEnabled(data.is_enabled === true);
                registration.activationId = data.id || registration.activationId;
                self.changeMessage(_('Workflow enabled.'), 'text-success');
            }
        }).fail(function(xhr) {
            const detail = xhr && xhr.responseJSON && xhr.responseJSON.message;
            const message = detail || _('Failed to update workflow activation.');
            self.changeMessage(message, 'text-danger');
            $osf.growl('Error', message);
            Raven.captureMessage('Failed to update workflow activation', {
                extra: {
                    url: url,
                    response: xhr && xhr.responseJSON,
                },
            });
        }).always(function() {
            self.togglingIds.remove(registration.id);
        });
    };

    $('#tokenPermissionModal').on('hidden.bs.modal', function() {
        if (self.tokenPermissionRequest.pendingPayload) {
            self.tokenPermissionRequest.pendingPayload = null;
            self.tokenPermissionRequest.creatorMode('none');
        }
    });

    $('#enableTokenPermissionModal').on('hidden.bs.modal', function() {
        if (self.enableTokenRequest.pendingRegistration) {
            self.enableTokenRequest.pendingRegistration = null;
            self.enableTokenRequest.creatorMode('none');
        }
    });

    $('#registrationEnableTokenPermissionModal').on('hidden.bs.modal', function() {
        if (self.registrationEnableTokenRequest.pendingRegistration) {
            self.registrationEnableTokenRequest.pendingRegistration = null;
            self.registrationEnableTokenRequest.creatorMode('none');
        }
    });

    $('#activateTokenPermissionModal').on('hidden.bs.modal', function() {
        if (self.activateTokenRequest.pendingRegistrationId) {
            self.activateTokenRequest.pendingRegistrationId = null;
            self.activateTokenRequest.managerMode('none');
        }
    });

    self.fetchEngines().always(function() {
        if (!self.hasEngines()) {
            const current = $.extend({}, self.errors());
            current.engineId = _('No workflow engines are available.');
            self.errors(current);
        }
        self.fetchRegistrations();
    });
}

$.extend(WorkflowNodeSettingsViewModel.prototype, ChangeMessageMixin.prototype);

function WorkflowNodeConfig(selector, options) {
    const viewModel = new WorkflowNodeSettingsViewModel(options);
    $osf.applyBindings(viewModel, selector);
    return viewModel;
}

module.exports = WorkflowNodeConfig;
