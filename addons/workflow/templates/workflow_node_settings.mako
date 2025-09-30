## -*- coding: utf-8 -*-
<div id="${addon_short_name}Scope" class="scripted">
    <h4 class="addon-title">
        <img class="addon-icon" src=${addon_icon_url}>
        ${addon_full_name}
    </h4>

    <div class="${addon_short_name}-settings">
        <div class="row" data-bind="if: isLoading">
            <div class="col-md-12 text-muted">
                <i class="fa fa-spinner fa-lg fa-spin"></i>
                ${_("Loading workflow registrations...")}
            </div>
        </div>

        <div class="row" data-bind="if: loadError">
            <div class="col-md-12">
                <div class="alert alert-danger" data-bind="text: loadError"></div>
            </div>
        </div>

        <div data-bind="if: !isLoading()">
            <div class="panel-group" style="margin-bottom: 15px;">
                <div class="panel panel-default">
                    <div class="panel-heading" style="cursor: pointer;" data-toggle="collapse" data-target="#localWorkflowsPanel" onclick="$(this).find('.toggle-icon').toggleClass('fa-chevron-down fa-chevron-right');">
                        <span style="font-size: 14px;">
                            <i class="fa fa-chevron-right toggle-icon"></i>
                            <strong>${_("Workflow Registrations")}</strong>
                            <span class="badge" data-bind="text: localRegistrations().length" style="margin-left: 5px;"></span>
                        </span>
                        <button type="button" class="btn btn-link btn-xs pull-right" data-bind="click: fetchRegistrations, disable: isRefreshing" onclick="event.stopPropagation();">
                            <i class="fa fa-refresh" data-bind="css: { 'fa-spin': isRefreshing }"></i>
                            ${_("Refresh")}
                        </button>
                    </div>
                    <div id="localWorkflowsPanel" class="panel-collapse collapse">
                        <!-- ko if: localRegistrations().length -->
                        <table class="table table-striped table-bordered table-condensed" style="margin-bottom: 0;">
                            <thead>
                                <tr>
                                    <th>${_("Label")}</th>
                                    <th>${_("Definition")}</th>
                                    <th>${_("Engine")}</th>
                                    <th>${_("Status")}</th>
                                    <th>${_("Actions")}</th>
                                </tr>
                            </thead>
                            <tbody data-bind="foreach: localRegistrations">
                                <tr>
                                    <td>
                                        <strong data-bind="text: label"></strong>
                                        <div class="text-muted" data-bind="text: description, visible: description"></div>
                                        <div class="text-muted small" data-bind="text: tokenSettingsDisplay, visible: tokenSettingsDisplay"></div>
                                    </td>
                                    <td>
                                        <div data-bind="text: definition_name || definition_id"></div>
                                        <small class="text-muted" data-bind="text: definition_id"></small>
                                    </td>
                                    <td>
                                        <span data-bind="text: engine_id"></span>
                                    </td>
                                    <td>
                                        <span class="label" data-bind="css: { 'label-success': isActive(), 'label-default': !isActive() }, text: isActive() ? activeLabel : inactiveLabel"></span>
                                    </td>
                                    <td class="text-nowrap">
                                        <button type="button"
                                                class="btn btn-xs btn-default"
                                                data-bind="click: $parent.toggleRegistrationActive,
                                                           css: { 'disabled': $parent.isToggling(id) },
                                                           attr: { disabled: $parent.isToggling(id) }">
                                            <span data-bind="text: isActive() ? disableLabel : enableLabel"></span>
                                        </button>
                                        <!-- ko if: !isActive() -->
                                        <button type="button"
                                                class="btn btn-xs btn-danger"
                                                data-bind="click: $parent.deleteRegistration,
                                                           css: { 'disabled': $parent.isDeleting(id) },
                                                           attr: { disabled: $parent.isDeleting(id) }">
                                            <i class="fa fa-trash"></i> ${_("Delete")}
                                        </button>
                                        <!-- /ko -->
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <!-- /ko -->
                        <!-- ko if: !localRegistrations().length -->
                        <div class="panel-body">
                            <span class="text-muted">${_("No workflows have been registered in this project yet.")}</span>
                        </div>
                        <!-- /ko -->

                        <div class="panel-body" style="background-color: #f9f9f9; border-top: 1px solid #ddd;">
                            <h5 style="margin-top: 0;"><strong>${_("Register new workflow")}</strong></h5>
                            <div>
                <form class="form-horizontal" data-bind="submit: submitRegistration">
                    <div class="form-group" data-bind="css: { 'has-error': errors().engineId }">
                        <label class="control-label col-sm-3" for="workflow-engine-id">${_("Engine")}</label>
                        <div class="col-sm-9">
                            <div data-bind="if: isLoadingEngines">
                                <p class="text-muted">
                                    <i class="fa fa-spinner fa-spin"></i>
                                    ${_("Loading available engines...")}
                                </p>
                            </div>
                            <div class="alert alert-warning" data-bind="visible: engineLoadError, text: engineLoadError"></div>
                            <div data-bind="if: !isLoadingEngines() && hasEngines()">
                                <select id="workflow-engine-id"
                                        class="form-control"
                                        data-bind="options: engines,
                                                   optionsValue: 'engine_id',
                                                   optionsText: 'display',
                                                   value: form.engineId,
                                                   optionsCaption: selectEngineCaption"></select>
                                <p class="help-block">
                                    ${_("Select the workflow engine that was registered by your administrator.")}
                                </p>
                            </div>
                            <p class="text-muted" data-bind="visible: !isLoadingEngines() && !hasEngines() && !engineLoadError()">
                                ${_("No workflow engines are currently available. Please contact your administrator.")}
                            </p>
                        </div>
                    </div>
                    <div data-bind="if: hasEngines()">
                    <div class="form-group">
                        <label class="control-label col-sm-3">${_("Definition Source")}</label>
                        <div class="col-sm-9">
                            <div class="radio">
                                <label>
                                    <input type="radio" name="definitionSource" value="existing"
                                           data-bind="checked: form.definitionSource">
                                    ${_("Select existing definition")}
                                </label>
                            </div>
                            <div class="radio">
                                <label data-bind="css: { 'text-muted': !canUploadWorkflowZip() }">
                                    <input type="radio" name="definitionSource" value="upload"
                                           data-bind="checked: form.definitionSource, enable: canUploadWorkflowZip">
                                    ${_("Upload workflow ZIP")}
                                    <span data-bind="visible: form.engineId() && !canUploadWorkflowZip()" class="text-danger small">
                                        (${_("Not allowed for this project")})
                                    </span>
                                </label>
                            </div>
                        </div>
                    </div>

                    <div class="form-group" data-bind="css: { 'has-error': errors().definitionId }, visible: form.definitionSource() === 'existing'">
                        <label class="control-label col-sm-3" for="workflow-definition-id">${_("Definition")}</label>
                        <div class="col-sm-9">
                            <p class="text-muted" data-bind="visible: !form.engineId()">
                                ${_("Select an engine to load available process definitions or enter an identifier manually.")}
                            </p>

                            <div data-bind="visible: form.engineId" style="margin-bottom: 0.5em;">
                                <div data-bind="if: isLoadingDefinitions">
                                    <p class="text-muted">
                                        <i class="fa fa-spinner fa-spin"></i>
                                        ${_("Loading definitions...")}
                                    </p>
                                </div>

                                <div class="alert alert-warning" data-bind="visible: definitionLoadError, text: definitionLoadError"></div>

                                <div data-bind="if: !isLoadingDefinitions() && hasDefinitions()">
                                    <div class="input-group">
                                        <select class="form-control"
                                                data-bind="options: definitions,
                                                           optionsValue: 'definition_id',
                                                           optionsText: 'display',
                                                           value: selectedDefinitionId,
                                                           optionsCaption: selectDefinitionCaption"></select>
                                        <span class="input-group-btn">
                                            <button type="button" class="btn btn-default" data-bind="click: refreshDefinitions, attr: { disabled: isLoadingDefinitions() }">
                                                <i class="fa fa-refresh" data-bind="css: { 'fa-spin': isLoadingDefinitions }"></i>
                                            </button>
                                        </span>
                                    </div>
                                </div>

                                <p class="text-muted" data-bind="visible: !isLoadingDefinitions() && !hasDefinitions() && !definitionLoadError()">
                                    ${_("This engine has no published definitions. Try refreshing after a definition is deployed.")}
                                </p>
                            </div>

                            <p class="text-danger" data-bind="text: errors().definitionId"></p>
                        </div>
                    </div>

                    <div class="form-group" data-bind="css: { 'has-error': errors().workflowZip }, visible: form.definitionSource() === 'upload'">
                        <label class="control-label col-sm-3" for="workflow-zip">${_("Workflow ZIP")}</label>
                        <div class="col-sm-9">
                            <input type="file" id="workflow-zip" accept=".zip"
                                   data-bind="event: { change: handleFileSelect }">
                            <p class="help-block">
                                ${_("Upload a ZIP file containing BPMN and form definitions exported from Flowable Design.")}
                            </p>
                            <div data-bind="if: form.selectedFile">
                                <p class="text-muted">
                                    <i class="fa fa-file-archive-o"></i>
                                    <span data-bind="text: form.selectedFile().name"></span>
                                    (<span data-bind="text: formatFileSize(form.selectedFile().size)"></span>)
                                </p>
                            </div>
                            <p class="text-danger" data-bind="text: errors().workflowZip"></p>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="control-label col-sm-3" for="workflow-label">${_("Display label")}</label>
                        <div class="col-sm-9">
                            <input id="workflow-label" type="text" class="form-control" data-bind="value: form.label" maxlength="255">
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="control-label col-sm-3" for="workflow-description">${_("Description")}</label>
                        <div class="col-sm-9">
                            <textarea id="workflow-description" class="form-control" rows="2" data-bind="value: form.description"></textarea>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="control-label col-sm-3">${_("Creator token")}</label>
                        <div class="col-sm-9">
                            <select class="form-control" data-bind="value: form.creatorTokenMode">
                                <option value="none">${_("Do not use")}</option>
                                <option value="read">${_("Use with Read permission")}</option>
                                <option value="readwrite">${_("Use with ReadWrite permission")}</option>
                            </select>
                            <p class="help-block">${_("Grant workflow access using the creator's credentials.")}</p>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="control-label col-sm-3">${_("Manager token")}</label>
                        <div class="col-sm-9">
                            <select class="form-control" data-bind="value: form.managerTokenMode">
                                <option value="none">${_("Do not use")}</option>
                                <option value="read">${_("Use with Read permission")}</option>
                                <option value="readwrite">${_("Use with ReadWrite permission")}</option>
                            </select>
                            <p class="help-block">${_("Grant workflow access using the project manager's credentials.")}</p>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="control-label col-sm-3">${_("Executor token")}</label>
                        <div class="col-sm-9">
                            <select class="form-control" data-bind="value: form.executorTokenMode">
                                <option value="none">${_("Do not use")}</option>
                                <option value="read">${_("Use with Read permission")}</option>
                                <option value="readwrite">${_("Use with ReadWrite permission")}</option>
                            </select>
                            <p class="help-block">${_("Grant workflow access using the executor's credentials.")}</p>
                        </div>
                    </div>
                    <div class="form-group">
                        <div class="col-sm-offset-3 col-sm-9">
                            <button type="submit" class="btn btn-primary" data-bind="disable: isSubmitting">
                                <span data-bind="visible: isSubmitting"><i class="fa fa-spinner fa-spin"></i> ${_("Registering")}</span>
                                <span data-bind="visible: !isSubmitting()">${_("Register workflow")}</span>
                            </button>
                        </div>
                    </div>
                    </div>
                </form>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="panel panel-default">
                    <div class="panel-heading" style="cursor: pointer;" data-toggle="collapse" data-target="#activationsPanel" onclick="$(this).find('.toggle-icon').toggleClass('fa-chevron-down fa-chevron-right');">
                        <span style="font-size: 14px;">
                            <i class="fa fa-chevron-down toggle-icon"></i>
                            <strong>${_("Workflow Activations")}</strong>
                            <span class="badge" data-bind="text: activations().length" style="margin-left: 5px;"></span>
                        </span>
                        <button type="button" class="btn btn-link btn-xs pull-right" data-bind="click: fetchRegistrations, disable: isRefreshing" onclick="event.stopPropagation();">
                            <i class="fa fa-refresh" data-bind="css: { 'fa-spin': isRefreshing }"></i>
                            ${_("Refresh")}
                        </button>
                    </div>
                    <div id="activationsPanel" class="panel-collapse collapse in">
                        <!-- ko if: activations().length -->
                        <table class="table table-striped table-bordered table-condensed" style="margin-bottom: 0;">
                            <thead>
                                <tr>
                                    <th>${_("Label")}</th>
                                    <th>${_("Definition")}</th>
                                    <th>${_("Engine")}</th>
                                    <th>${_("Defined in")}</th>
                                    <th>${_("Actions")}</th>
                                </tr>
                            </thead>
                            <tbody data-bind="foreach: activations">
                                <tr>
                                    <td>
                                        <strong data-bind="text: label"></strong>
                                        <div class="text-muted" data-bind="text: description, visible: description"></div>
                                    </td>
                                    <td>
                                        <div data-bind="text: definition_name || definition_id"></div>
                                        <small class="text-muted" data-bind="text: definition_id"></small>
                                    </td>
                                    <td>
                                        <span data-bind="text: engine_id"></span>
                                    </td>
                                    <td>
                                        <a data-bind="visible: nodeUrl, attr: { href: nodeUrl }, text: node_title"></a>
                                        <span data-bind="visible: !nodeUrl, text: isLocal ? 'This project' : 'Shared'"></span>
                                    </td>
                                    <td class="text-nowrap">
                                        <button type="button"
                                                class="btn btn-xs btn-default"
                                                data-bind="click: $parent.deactivateWorkflow,
                                                           css: { 'disabled': $parent.isToggling(id) },
                                                           attr: { disabled: $parent.isToggling(id) }">
                                            <span data-bind="text: disableLabel"></span>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <!-- /ko -->
                        <!-- ko if: !activations().length -->
                        <div class="panel-body">
                            <span class="text-muted">${_("No workflows are currently activated.")}</span>
                        </div>
                        <!-- /ko -->

                        <div class="panel-body" style="background-color: #f9f9f9; border-top: 1px solid #ddd;">
                            <h5 style="margin-top: 0;"><strong>${_("Activate workflow")}</strong></h5>
                            <form class="form-horizontal" data-bind="submit: activateWorkflow">
                                <div class="form-group">
                                    <label class="control-label col-sm-3" for="activate-workflow-select">${_("Workflow")}</label>
                                    <div class="col-sm-9">
                                        <select id="activate-workflow-select"
                                                class="form-control"
                                                data-bind="options: availableRegistrationsForActivation,
                                                           optionsValue: 'id',
                                                           optionsText: function(item) { return item.label() || item.definition_name || item.definition_id; },
                                                           value: activateForm.selectedRegistrationId,
                                                           optionsCaption: 'Select a workflow…'"></select>
                                        <p class="help-block">${_("Select a workflow to activate in this project.")}</p>
                                    </div>
                                </div>
                                <div class="form-group">
                                    <div class="col-sm-offset-3 col-sm-9">
                                        <button type="submit" class="btn btn-primary" data-bind="disable: isSubmitting() || !activateForm.selectedRegistrationId()">
                                            <span data-bind="visible: isSubmitting"><i class="fa fa-spinner fa-spin"></i> ${_("Activating")}</span>
                                            <span data-bind="visible: !isSubmitting()">${_("Activate")}</span>
                                        </button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>

    <div class="modal fade" id="tokenPermissionModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <h4 class="modal-title">${_("Grant Workflow Permissions")}</h4>
                </div>
                <div class="modal-body">
                    <p>${_("This workflow will use your credentials to access project resources.")}</p>
                    <div data-bind="if: tokenPermissionRequest.creatorMode() !== 'none'">
                        <h5><strong>${_("Creator Token")}</strong></h5>
                        <p data-bind="text: tokenPermissionRequest.creatorModeLabel"></p>
                        <p class="text-muted">${_("The workflow can perform the following actions on your behalf:")}</p>
                        <ul class="text-muted">
                            <li>${_("Read and write files")}</li>
                            <li>${_("Update metadata")}</li>
                            <li>${_("Post comments")}</li>
                            <li>${_("Access connected services (e.g., WEKO)")}</li>
                        </ul>
                    </div>
                    <div class="alert alert-warning">
                        <i class="fa fa-exclamation-triangle"></i>
                        ${_("Only grant permissions to workflows you trust.")}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</button>
                    <button type="button" class="btn btn-primary" data-bind="click: confirmTokenPermission">
                        ${_("Grant Permission and Register")}
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="enableTokenPermissionModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <h4 class="modal-title">${_("Re-grant Workflow Permissions")}</h4>
                </div>
                <div class="modal-body">
                    <p>${_("Enabling this workflow will re-issue your Creator Token to access project resources.")}</p>
                    <div data-bind="if: enableTokenRequest.creatorMode() !== 'none'">
                        <h5><strong>${_("Creator Token")}</strong></h5>
                        <p data-bind="text: enableTokenRequest.creatorModeLabel"></p>
                        <p class="text-muted">${_("The workflow can perform the following actions on your behalf:")}</p>
                        <ul class="text-muted">
                            <li>${_("Read and write files")}</li>
                            <li>${_("Update metadata")}</li>
                            <li>${_("Post comments")}</li>
                            <li>${_("Access connected services (e.g., WEKO)")}</li>
                        </ul>
                    </div>
                    <div class="alert alert-warning">
                        <i class="fa fa-exclamation-triangle"></i>
                        ${_("Only grant permissions to workflows you trust.")}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</button>
                    <button type="button" class="btn btn-primary" data-bind="click: confirmEnableToken">
                        ${_("Grant Permission and Enable")}
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="registrationEnableTokenPermissionModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <h4 class="modal-title">${_("Grant Workflow Permissions")}</h4>
                </div>
                <div class="modal-body">
                    <p>${_("Enabling this workflow registration will issue your Creator Token to access project resources.")}</p>
                    <div data-bind="if: registrationEnableTokenRequest.creatorMode() !== 'none'">
                        <h5><strong>${_("Creator Token")}</strong></h5>
                        <p data-bind="text: registrationEnableTokenRequest.creatorModeLabel"></p>
                        <p class="text-muted">${_("The workflow can perform the following actions on your behalf:")}</p>
                        <ul class="text-muted">
                            <li>${_("Read and write files")}</li>
                            <li>${_("Update metadata")}</li>
                            <li>${_("Post comments")}</li>
                            <li>${_("Access connected services (e.g., WEKO)")}</li>
                        </ul>
                    </div>
                    <div class="alert alert-warning">
                        <i class="fa fa-exclamation-triangle"></i>
                        ${_("Only grant permissions to workflows you trust.")}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</button>
                    <button type="button" class="btn btn-primary" data-bind="click: confirmRegistrationEnableToken">
                        ${_("Grant Permission and Enable")}
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="activateTokenPermissionModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <h4 class="modal-title">${_("Grant Workflow Permissions")}</h4>
                </div>
                <div class="modal-body">
                    <p>${_("Activating this workflow will issue your Manager Token to access project resources.")}</p>
                    <div data-bind="if: activateTokenRequest.managerMode() !== 'none'">
                        <h5><strong>${_("Manager Token")}</strong></h5>
                        <p data-bind="text: activateTokenRequest.managerModeLabel"></p>
                        <p class="text-muted">${_("The workflow can perform the following actions on your behalf:")}</p>
                        <ul class="text-muted">
                            <li>${_("Read and write files")}</li>
                            <li>${_("Update metadata")}</li>
                            <li>${_("Post comments")}</li>
                            <li>${_("Access connected services (e.g., WEKO)")}</li>
                        </ul>
                    </div>
                    <div class="alert alert-warning">
                        <i class="fa fa-exclamation-triangle"></i>
                        ${_("Only grant permissions to workflows you trust.")}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</button>
                    <button type="button" class="btn btn-primary" data-bind="click: confirmActivateToken">
                        ${_("Grant Permission and Activate")}
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="deleteRegistrationModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <h4 class="modal-title">${_("Delete Workflow Registration")}</h4>
                </div>
                <div class="modal-body">
                    <p data-bind="if: deleteRegistrationRequest.pendingRegistration">
                        ${_("Are you sure you want to delete")}
                        <strong data-bind="text: deleteRegistrationRequest.pendingRegistration().label"></strong>?
                    </p>
                    <div class="alert alert-danger">
                        <i class="fa fa-exclamation-triangle"></i>
                        <strong>${_("This action cannot be undone.")}</strong>
                        <p class="m-t-sm">${_("All associated workflow activations and delegation tokens will be revoked and removed.")}</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</button>
                    <button type="button" class="btn btn-danger" data-bind="click: confirmDeleteRegistration">
                        <i class="fa fa-trash"></i> ${_("Delete")}
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
