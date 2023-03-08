'use strict';

var ko = require('knockout');
var m = require('mithril');
var URI = require('URIjs');
var $ = require('jquery');
var Raven = require('raven-js');
const crypto = require('crypto');

var Fangorn = require('js/fangorn').Fangorn;
var waterbutler = require('js/waterbutler');
var $osf = require('js/osfHelpers');

function changeState(grid, item, version) {
    item.data.version = version;
    grid.updateFolder(null, item);
}

// Define Fangorn Button Actions
var _wekoItemButtons = {
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
                    }, 'View'));
            } else if ((item.data.extra || {}).weko === 'draft') {
                buttons.push(m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        _publish(tb, item, item.data);
                    },
                    icon: 'fa fa-upload',
                    className: 'text-primary weko-button-publish'
                }, 'Publish'));
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
            }else{
                return m.component(Fangorn.Components.defaultItemButtons,
                                      {treebeard : tb, mode : mode, item : item });
            }
        }
        return m('span', buttons);
    }
};

function gotoItem (item) {
    const itemId = /\/weko:item([0-9]+)\/$/.exec(item.data.path)[1];

    $.getJSON(item.data.nodeApiUrl + 'weko/item/' + itemId + '/').done(function (data) {
        window.open(data.url, '_blank');
    });
}

function _fangornFolderIcons(item) {
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

function _fangornWEKOTitle(item, col) {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) {
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }
    if (item.data.addonFullname) {
        var contents = [m('weko-name', item.data.name)];
        return m('span', contents);
    } else {
        const contents = [
            m('weko-name.fg-file-links',
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

function _fangornColumns(item) {
    var tb = this;
    var columns = [];
    columns.push({
        data : 'name',
        folderIcons : true,
        filter : true,
        custom: _fangornWEKOTitle
    });
    return columns;
}

function _getWaterbutlerUrl() {
    var url = contextVars.waterbutlerURL;
    if(! url.endsWith('/')) {
        url += '/';
    }
    url += 'v1/resources/' + contextVars.node.id + '/providers/weko';
    return url;
}

function _getWaterbutlerParentUrl(parentItem) {
    if(parentItem.data.materialized !== undefined) {
        return _getWaterbutlerUrl() + parentItem.data.materialized;
    }else{
        return _getWaterbutlerUrl() + '/';
    }
}

function _findItem(item, item_id) {
    if(item.id == item_id) {
        return item;
    }else if(item.children){
        for(var i = 0; i < item.children.length; i ++) {
            var found = _findItem(item.children[i], item_id);
            if(found) {
                return found;
            }
        }
    }
    return null;
}

function _showError(tb, message) {
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

function _publish(tb, contextItem, itemData) {
    console.log('publish', contextItem);
    const extra = contextItem.data.extra;
    var url = contextVars.node.urls.api;
    if (!url.match(/.*\/$/)) {
        url += '/';
    }
    url += 'weko/index/' + extra.index
        + '/files/' + contextItem.data.nodeId + '/' + extra.source.provider
        + extra.source.materialized_path;
    //osfBlock.block();
    return $.ajax({
        url: url,
        type: 'PUT',
        dataType: 'json'
    }).done(function (data) {
      //osfBlock.unblock();
    }).fail(function(xhr, status, error) {
      //osfBlock.unblock();
      Raven.captureMessage('Error while publishing file', {
        extra: {
            url: url,
            status: status,
            error: error
        }
      });
    });
}

function _uploadSuccess(file, item, response) {
    var tb = this;
    console.log('Uploaded', item, response);
    if(response.data.attributes.extra.archivable) {
        console.log('Publishing...', response);
        _publish(tb, item, response.data.attributes);
    }else{
        tb.updateFolder(null, _findItem(tb.treeData, item.parentID));
    }
    return {};
}

Fangorn.config.weko = {
    folderIcon: _fangornFolderIcons,
    uploadSuccess: _uploadSuccess,
    itemButtons: _wekoItemButtons,
    resolveRows: _fangornColumns
};
