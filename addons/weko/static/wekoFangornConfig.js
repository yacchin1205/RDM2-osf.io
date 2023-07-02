'use strict';

const ko = require('knockout');
const m = require('mithril');
const $ = require('jquery');
const Raven = require('raven-js');

const fangorn = require('js/fangorn');
const Fangorn = fangorn.Fangorn;
const $osf = require('js/osfHelpers');

const _ = require('js/rdmGettext')._;
const sprintf = require('agh.sprintf').sprintf;

const logPrefix = '[weko]';
const refreshingIds = {};
const metadataRefreshingRetries = 3;
const metadataRefreshingTimeout = 1000;
const metadataRefreshingTimeoutExp = 2;
var fileViewButtons = null;
var hashProcessed = false;
var uploadCount = 0;
var uploadReservedHandler = null;

// Define Fangorn Button Actions
const wekoItemButtons = {
    view: function (ctrl, args, children) {
        const buttons = [];
        const tb = args.treebeard;
        const item = args.item;
        const mode = tb.toolbarMode;

        if (tb.options.placement !== 'fileview') {
            if ((item.data.extra || {}).weko === 'item') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function(event) {
                            gotoItem(item);
                        },
                        icon: 'fa fa-external-link',
                        className : 'text-info'
                    }, _('View')));
                const aritem = Object.assign({}, item);
                aritem.data = Object.assign({}, item.data, {
                    permissions: {
                        view: true,
                        edit: false
                    }
                });
                buttons.push(
                    m.component(Fangorn.Components.defaultItemButtons,
                        {treebeard : tb, mode : mode, item : aritem })
                );
            } else if ((item.data.extra || {}).weko === 'index') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function(event) {
                            gotoItem(item);
                        },
                        icon: 'fa fa-external-link',
                        className : 'text-info'
                    }, _('View')));
                const aritem = Object.assign({}, item);
                aritem.data = Object.assign({}, item.data, {
                    permissions: {
                        view: true,
                        edit: true
                    }
                });
                buttons.push(
                    m.component(Fangorn.Components.defaultItemButtons,
                        {treebeard : tb, mode : mode, item : aritem })
                );
            } else if ((item.data.extra || {}).weko === 'draft') {
                buttons.push(m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        deposit(tb, item);
                    },
                    icon: 'fa fa-upload',
                    className: 'text-primary weko-button-publish'
                }, _('Deposit')));
                buttons.push(m.component(Fangorn.Components.defaultItemButtons, {
                    treebeard : tb, mode : mode, item : item
                }));
            } else if ((item.data.extra || {}).weko === 'file') {
                const aritem = Object.assign({}, item);
                aritem.data = Object.assign({}, item.data, {
                    permissions: {
                        view: true,
                        edit: false
                    }
                });
                return m.component(Fangorn.Components.defaultItemButtons,
                    {treebeard : tb, mode : mode, item : aritem });
            } else if ((item.data.extra || {}).weko) {
                console.warn('Unknown weko metadata type: ', (item.data.extra || {}).weko);
            } else if (item.data.kind === 'folder' && item.data.addonFullname) {
                const aritem = Object.assign({}, item);
                aritem.data = Object.assign({}, item.data, {
                    permissions: {
                        view: true,
                        edit: true
                    }
                });
                return m.component(Fangorn.Components.defaultItemButtons,
                    {treebeard : tb, mode : mode, item : aritem });
            } else {
                return m.component(Fangorn.Components.defaultItemButtons,
                                      {treebeard : tb, mode : mode, item : item });
            }
        }
        return m('span', buttons);
    }
};

function gotoItem (item) {
    if (item.data && item.data.extra && item.data.extra.weko === 'draft') {
        const url = fangorn.getPersistentLinkFor(item);
        window.location.href = url;
        return;
    }
    if (!(item.data.extra || {}).weko_web_url) {
        throw new Error('Missing properties');
    }
    window.open(item.data.extra.weko_web_url, '_blank');
}

function wekoFolderIcons(item) {
    if (item.data.iconUrl) {
        return m('img', {
            src: item.data.iconUrl,
            style: {
                width: '16px',
                height: 'auto'
            }
        }, ' ');
    }
    return undefined;
}

function wekoWEKOTitle(item, col) {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) {
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }
    if (item.data.addonFullname) {
        return m('span', [m('span', item.data.name)]);
    } else {
        const contents = [
            m('span.fg-file-links',
                {
                    onclick: function () {
                        gotoItem(item);
                    }
                },
                item.data.name
            )
        ];
        if ((item.data.extra || {}).weko === 'draft') {
            contents.push(
                m('span.text.text-muted', ' [Draft]')
            );
        }
        return m('span', contents);
    }
}

function wekoColumns(item) {
    const treebeard = this;
    checkAndReserveRefreshingMetadata(
        item,
        function(item) {
            const parentItem = findItem(treebeard.treeData, item.parentID);
            reserveDeposit(treebeard, item, function() {
                treebeard.updateFolder(null, parentItem);
            });
        }
    );
    var tb = this;
    var columns = [];
    columns.push({
        data : 'name',
        folderIcons : true,
        filter : true,
        custom: wekoWEKOTitle
    });
    item.css = (item.css || '') + ' weko-row';
    return columns;
}

function findItem(item, item_id) {
    if(item.id == item_id) {
        return item;
    }else if(item.children){
        for(var i = 0; i < item.children.length; i ++) {
            const found = findItem(item.children[i], item_id);
            if(found) {
                return found;
            }
        }
    }
    return null;
}

function showError(tb, message) {
    if (!tb) {
        $osf.growl('WEKO3 Error:', message);
        return;
    }
    var modalContent = [
            m('p.m-md', message)
        ];
    var modalActions = [
            m('button.btn.btn-primary', {
                    'onclick': function () {
                        tb.modal.dismiss();
                    }
                }, 'Okay')
        ];
    tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', 'Error'));
}

function performDeposit(tb, contextItem) {
    console.log(logPrefix, 'publish', contextItem);
    const extra = contextItem.data.extra;
    var url = contextVars.node.urls.api;
    if (!url.match(/.*\/$/)) {
        url += '/';
    }
    url += 'weko/index/' + extra.index
        + '/files/' + contextItem.data.nodeId + '/' + contextItem.data.provider
        + contextItem.data.materialized;
    startDepositing(tb, contextItem);
    return $osf.putJSON(url, {
        content_path: extra.source.provider + extra.source.materialized_path,
        after_delete_path: contextItem.data.path,
    }).done(function (data) {
      console.log(logPrefix, 'checking progress...');
      checkDepositing(tb, contextItem, url);
    }).fail(function(xhr, status, error) {
      cancelDepositing(tb, contextItem);
      const message = _('Error occurred: ') + error;
      showError(tb, message);
      Raven.captureMessage('Error while depositing file', {
        extra: {
            url: url,
            status: status,
            error: error
        }
      });
    });
}

function checkDepositing(tb, contextItem, url) {
    return $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
        console.log(logPrefix, 'loaded: ', data);
        if (data.data && data.data.attributes && data.data.attributes.error) {
            cancelDepositing(tb, contextItem);
            const message = _('Error occurred: ') + data.data.attributes.error;
            showError(tb, message);
            return;
        }
        if (data.data && data.data.attributes && data.data.attributes.result) {
            console.log(logPrefix, 'uploaded', data.data.attributes.result);
            if (tb) {
                tb.updateFolder(null, findItem(tb.treeData, contextItem.parentID));
            } else {
                $('#weko-deposit i')
                    .addClass('fa-upload')
                    .removeClass('fa-spinner fa-pulse');
                $('#weko-deposit').removeClass('disabled');
                $osf.growl('Success', _('Deposit was successful.'), 'success');
                const baseUrl = contextVars.node.urls.web + 'files/dir/' + contextItem.data.provider;
                const index = contextItem.data.materialized.lastIndexOf('/');
                window.location.href = baseUrl + contextItem.data.materialized.substring(0, index + 1);
            }
            return;
        }
        if (data.data && data.data.attributes && data.data.attributes.progress) {
            contextItem.data.progress = data.data.attributes.progress.rate || 0;
            contextItem.data.uploadState = function() {
                return 'uploading';
            };
            if (tb) {
                tb.redraw();
            }
        }
        setTimeout(function() {
            checkDepositing(tb, contextItem, url);
        }, 1000);
    }).fail(function(xhr, status, error) {
        if (status === 'error' && error === 'NOT FOUND') {
            setTimeout(function() {
                checkDepositing(tb, contextItem, url);
            }, 1000);
            return;
        }
        cancelDepositing(tb, contextItem);
        const message = _('Error occurred: ') + error;
        showError(tb, message);
        Raven.captureMessage('Error while retrieving addon info', {
            extra: {
                url: url,
                status: status,
                error: error
            }
        });
    });
}

function startDepositing(tb, item) {
    if (!tb) {
        $('#weko-deposit i')
            .removeClass('fa-upload')
            .addClass('fa-spinner fa-pulse');
        $('#weko-deposit').addClass('disabled');
        return;
    }
    item.inProgress = true;
    item.data.progress = 0;
    item.data.uploadState = function() {
        return 'pending';
    };
    tb.redraw();
}

function cancelDepositing(tb, item) {
    if (!tb) {
        $('#weko-deposit i')
            .addClass('fa-upload')
            .removeClass('fa-spinner fa-pulse');
        $('#weko-deposit').removeClass('disabled');
        return;
    }
    item.inProgress = false;
    item.data.progress = 100;
    item.data.uploadState = null;
    tb.redraw();
}

function reserveDeposit(treebeard, item, cancelCallback) {
    if (uploadCount <= 0) {
        deposit(treebeard, item, cancelCallback);
        return;
    }
    if (uploadReservedHandler) {
        console.warn(logPrefix, 'Upload handler already reserved', item);
        return;
    }
    console.log(logPrefix, 'Reserve upload handler', item);
    uploadReservedHandler = function() {
        deposit(treebeard, item, cancelCallback);
    };
}

function deposit(treebeard, item, cancelCallback) {
    showConfirmDeposit(treebeard, item, function(deposit) {
        if (!deposit) {
            if (!cancelCallback) {
                return;
            }
            cancelCallback();
            return;
        }
        performDeposit(treebeard, item);
    });
}

function showConfirmDeposit(tb, contextItem, callback) {
    const okHandler = function (dismiss) {
        dismiss()
        if (!callback) {
            return;
        }
        callback(true);
    };
    const cancelHandler = function (dismiss) {
        dismiss()
        if (!callback) {
            return;
        }
        callback(false);
    };
    const message = sprintf(
        _('Do you want to deposit the file/folder "%1$s" to WEKO? This operation is irreversible.'),
        $osf.htmlEscape(contextItem.data.name)
    );
    if (!tb) {
        const dialog = $('<div class="modal fade" data-backdrop="static"></div>');
        const close = $('<a href="#" class="btn btn-default" data-dismiss="modal"></a>').text(_('Cancel'));
        close.click(function() {
            cancelHandler(function() {
                dialog.modal('hide');
            });
        });
        const save = $('<a href="#" class="btn btn-primary"></a>').text(_('OK'));
        save.click(function() {
            okHandler(function() {
                dialog.modal('hide');
            });
        });
        const toolbar = $('<div></div>');
        const container = $('<ul></ul>').css('padding', '0 20px');
        dialog
            .append($('<div class="modal-dialog modal-lg"></div>')
                .append($('<div class="modal-content"></div>')
                    .append($('<div class="modal-header"></div>')
                        .append($('<h3></h3>').text(_('Deposit files'))))
                    .append($('<div class="modal-body"></div>')
                        .append(message))
                    .append($('<div class="modal-footer"></div>')
                        .css('display', 'flex')
                        .css('align-items', 'center')
                        .append(close.css('margin-left', 'auto'))
                        .append(save))));
        dialog.appendTo($('#treeGrid'));
        dialog.modal('show');
        return;
    }
    var modalContent = [
            m('p.m-md', message)
        ];
    var modalActions = [
            m('button.btn.btn-default', {
                    'onclick': function() {
                        cancelHandler(function() {
                            tb.modal.dismiss();
                        });
                    }
                }, _('Cancel')),
            m('button.btn.btn-primary', {
                    'onclick': function() {
                        okHandler(function() {
                            tb.modal.dismiss();
                        });
                    }
                }, _('OK'))
        ];
    tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', _('Deposit files')));
}

function checkAndReserveRefreshingMetadata(item, callback) {
    if (!item.data) {
        return;
    }
    const id = item.data.id;
    if (refreshingIds[id]) {
        // Already reserved
        return;
    }
    const metadatas = searchMetadatas(item);
    if (metadatas.length === 0 || metadatas.some(function(m) {
        return m.metadata === undefined;
    })) {
        // Not loaded
        return;
    }
    if (metadatas.every(function(m) {
        return m.metadata;
    })) {
        // Already loaded
        return;
    }
    refreshingIds[id] = Date.now();
    reserveMetadataRefresh(
        item,
        metadataRefreshingTimeout,
        metadataRefreshingRetries,
        callback
    );
}

function reserveMetadataRefresh(item, timeout, retries, callback) {
    console.log(logPrefix, 'reserveRefreshMetadata', item);
    setTimeout(function() {
        contextVars.metadata.loadMetadata(
            item.data.nodeId,
            item.data.nodeApiUrl,
            function() {
                const metadatas = searchMetadatas(item);
                if (metadatas.length > 0 && metadatas.every(function(m) {
                    return m.metadata;
                })) {
                    console.log(logPrefix, 'metadata refreshed', metadatas, item);
                    refreshingIds[item.data.id] = null;
                    if (!callback) {
                        return;
                    }
                    callback(item);
                    return;
                }
                console.log(logPrefix, 'refreshMetadata', metadatas, item);
                if (retries <= 0) {
                    console.log(logPrefix, 'Metadata refreshing cancelled', item);
                    return;
                }
                reserveMetadataRefresh(
                    item,
                    timeout * metadataRefreshingTimeoutExp,
                    retries - 1,
                    callback
                );
            }
        );
    }, timeout);
}

function searchMetadatas(tree, recursive) {
    const data = tree.data;
    var r = [];
    if (data.extra && data.extra.weko === 'draft' && isTopLevelDraft(tree)) {
        const metadata = contextVars.metadata.getMetadata(
            data.nodeId,
            data.provider + data.materialized
        );
        r.push({
            metadata: metadata,
            item: tree
        });
    } else if (recursive && ((data.extra && data.extra.weko === 'index') || data.addonFullname === 'WEKO')) {
        (tree.children || []).forEach(function(item) {
            r = r.concat(searchMetadatas(item, recursive));
        });
    }
    return r;
}

function isTopLevelDraft(item) {
    const data = item.data;
    if (!data) {
        return false;
    }
    const extra = data.extra;
    if (!extra) {
        return false;
    }
    const source = extra.source;
    if (!source) {
        return false;
    }
    const path = source.materialized_path;
    if (!path) {
        return false;
    }
    return path.match(/^\/\.weko\/[^\/]+\/[^\/]+\/?$/);
}

function refreshFileViewButtons(item) {
    if (item.data.provider !== 'weko') {
        return;
    }
    if (!isTopLevelDraft(item)) {
        return;
    }
    if (!fileViewButtons) {
        fileViewButtons = $('<div></div>')
            .addClass('btn-group m-t-xs')
            .attr('id', 'weko-toolbar');
    }
    const buttons = fileViewButtons;
    buttons.empty();
    const btn = $('<button></button>')
        .addClass('btn')
        .addClass('btn-sm')
        .addClass('btn-primary')
        .attr('id', 'weko-deposit');
    btn.append($('<i></i>').addClass('fa fa-upload'));
    btn.click(function(event) {
        deposit(null, item);
    });
    btn.append($('<span></span>').text(_('Deposit')));
    buttons.append(btn);
    $('#toggleBar .btn-toolbar').append(fileViewButtons);
}

function processHash(item) {
    if (hashProcessed) {
        return;
    }
    if (window.location.hash !== '#deposit') {
        return;
    }
    if (item.data.provider !== 'weko') {
        return;
    }
    hashProcessed = true;
    deposit(null, item);
}

function initFileView() {
    const observer = new MutationObserver(refreshIfToolbarExists);
    function refreshIfToolbarExists() {
        const toolbar = $('#toggleBar .btn-toolbar');
        if (toolbar.length === 0) {
            return;
        }
        const item = {
            data: Object.assign(
                {},
                contextVars.file,
                {
                    nodeId: contextVars.node.id,
                    nodeApiUrl: contextVars.node.urls.api,
                    materialized: contextVars.file.materialized || contextVars.file.materializedPath
                }
            )
        };
        refreshFileViewButtons(item);
        setTimeout(function() {
            processHash(item);
        }, 0);
    }
    const toggleBar = $('#toggleBar').get(0);
    observer.observe(toggleBar, {attributes: false, childList: true, subtree: false});
}

function wekoUploadAdd(file, item) {
    console.log(logPrefix, 'Detected: uploadAdded', file);
    uploadCount ++;
}

function wekoUploadSuccess(file, row) {
    console.log(logPrefix, 'Detected: uploadSuccess', file);
    uploadCount --;
    if (!uploadReservedHandler) {
        return;
    }
    if (uploadCount > 0) {
        console.log(logPrefix, 'Reserved upload handler exists. waiting for ', uploadCount, ' files');
        return;
    }
    console.log(logPrefix, 'Processing reserved upload handler...');
    const f = uploadReservedHandler;
    uploadReservedHandler = null;
    setTimeout(function() {
        // If uploadAdded is called immediately afterwards, then revert to the reserved state again.
        if (uploadCount > 0) {
            console.log(logPrefix, 'Reserved upload handler restored');
            uploadReservedHandler = f;
            return;
        }
        f();
        console.log(logPrefix, 'Reserved upload handler processed');
    }, 500);
}

Fangorn.config.weko = {
    folderIcon: wekoFolderIcons,
    itemButtons: wekoItemButtons,
    resolveRows: wekoColumns,
    uploadAdd: wekoUploadAdd,
    uploadSuccess: wekoUploadSuccess,
};

if ($('#fileViewPanelLeft').length > 0) {
    // File View
    initFileView();
}