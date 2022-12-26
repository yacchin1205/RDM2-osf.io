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

function _getLastPathComponent(path, isFolder) {
    const pathcomps = path.split('/');
    if(isFolder) {
        return pathcomps[pathcomps.length - 2];
    } else {
        return pathcomps[pathcomps.length - 1];
    }
}

function getLastPathComponent(itemData) {
    if(itemData.path === undefined) {
        return undefined;
    }
    return _getLastPathComponent(itemData.path, itemData.kind === 'folder');
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
                        _publish(tb, _findItem(tb.treeData, item.parentID),
                                 item, item.data);
                    },
                    icon: 'fa fa-upload',
                    className: 'text-primary weko-button-publish'
                }, 'Publish'));
            } else if ((item.data.extra || {}).weko) {
                ;
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

function _putMetadata(tb, parentItem, contextItem, draftFilename,
                      importFilename, importContent, dismissCallback) {
    $.ajax({
        type: 'GET',
        url: _getWaterbutlerParentUrl(parentItem),
        dataType: 'json',
        xhrFields:{withCredentials: true},
        success: function(data) {
            console.log(data);
            var jsonFiles = data.data.filter(function(d) {
                if(d.attributes && d.type == 'files') {
                    if(d.attributes.name == importFilename) {
                        return true;
                    }
                }
                return false;
              });
            var putUrl = null;
            var links = parentItem.data.links;
            var qsep = '&';
            if(links === undefined) {
                links = {'upload': _getWaterbutlerUrl() + '/'};
                qsep = '?';
            }
            if(jsonFiles.length == 0) {
                // Create file
                putUrl = links.upload + qsep + 'name=' + encodeURI(importFilename);
            }else{
                // Update file
                var baseUrl = links.upload;
                baseUrl = baseUrl.substring(0, baseUrl.lastIndexOf('/') + 1);
                putUrl =  baseUrl + encodeURI(importFilename);
            }
            console.log('Updating/Creating... ', putUrl);
            $.ajax({
                type: 'PUT',
                url: putUrl,
                dataType: 'json',
                data: importContent,
                xhrFields:{withCredentials: true},
                success: function(data) {
                    console.log(data);
                    var indexId = null;
                    if(parentItem.data.extra) {
                        indexId = parentItem.data.extra.indexId;
                    }
                    $osf.postJSON(
                            parentItem.data.nodeApiUrl + 'weko/item_log/',
                            ko.toJS({
                                index_id: indexId,
                                title: draftFilename
                            })
                        ).done(function(item){
                            console.log('Log added');
                            if(contextItem) {
                                contextItem.notify.update('Successfully published.',
                                                         'success', undefined, 1000);
                            }
                            setTimeout(dismissCallback, 1500)
                        });
                },
                error: function(xhr, textStatus, errorThrown) {
                    console.log('Error: ' + textStatus);
                    console.log(errorThrown);
                    var message = 'Error: Something went wrong when putting item. ' + textStatus;
                    _showError(tb, message);
                    dismissCallback();
                }});
        },
        error: function(xhr, textStatus, errorThrown) {
            console.log('Error: ' + textStatus, errorThrown);
            var message = 'Error: Something went wrong when retrieving item. ' + textStatus;
            _showError(tb, message);
            dismissCallback();
        }});
}

/*
function _submitDraft(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback) {
    if(metadata.asWEKOExport) {
        _submitDraftZip(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback);
    }else{
        _submitDraftXml(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback);
    }
}

function _submitDraftXml(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback) {
    console.log('confirmed', metadata, draftFileData, parentItem);
    var draftFilename = getLastPathComponent(draftFileData);
    var importXmlFilename = draftFilename + '-import.xml';
    $.get(window.contextVars.node.urls.api + 'weko/metadata/',
          ko.toJS({filename: draftFilename,
                   filenames: draftFileData.extra.content_files.join('\n'),
                   serviceItemType: metadata.serviceItemType})
        ).done(function(importXml){
            console.log('Generated', importXml);
            _putMetadata(tb, parentItem, contextItem, draftFilename,
                         importXmlFilename,
                         new XMLSerializer().serializeToString(importXml),
                         dismissCallback);
        });
}

function _submitDraftZip(tb, parentItem, contextItem, draftFileData, metadata, dismissCallback) {
    console.log('confirmed', metadata, draftFileData, parentItem);
    var draftFilename = getLastPathComponent(draftFileData);
    var importZipFilename = draftFilename + '-import.zipimport';
    _putMetadata(tb, parentItem, contextItem, draftFilename, importZipFilename,
                 '', dismissCallback);
}
*/

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

/*
function _publish(tb, parentItem, contextItem, itemData) {
    const url = contextVars.node.urls.api + 'metadata/project';
    $.getJSON(url).done(function (data) {
        const hash = computeHash(contextItem);
        const draftFilename = getLastPathComponent(itemData);
        const fileMetadatas = ((data.data.attributes || {}).files || [])
            .filter((file) => _getLastPathComponent(file.path, file.folder) === draftFilename);
        const fileMetadata = fileMetadatas.length === 0 ? { items: [] } : fileMetadatas[0];
        const metadataFilename = '.' + draftFilename + '-metadata.json';
        console.log('Metadata loaded', data, contextItem.data.materialized, hash);
        const dismissCallback = function() {
            console.log('Dismissed');
        };
        _putMetadata(tb, parentItem, contextItem, draftFilename,
            metadataFilename,
            JSON.stringify(fileMetadata),
            dismissCallback);
    }).fail(function (xhr, status, error) {
        console.log('Error: ' + status, error);
        var message = 'Error: Something went wrong when retrieving serviceitemtype. ' + status;
        _showError(tb, message);
        $('.weko-button-publish i').attr('class', 'fa fa-upload');
    });
}

function _publish(tb, parentItem, contextItem, itemData) {
    $('.weko-button-publish i').attr('class', 'fa fa-spinner fa-pulse fa-3x fa-fw');
    if(itemData.extra.content_files.length == 0) {
        console.log('loading', itemData);
        $.ajax({
            type: 'GET',
            url: _getWaterbutlerParentUrl(parentItem),
            dataType: 'json',
            xhrFields:{withCredentials: true},
            success: function(data) {
                var jsonFiles = data.data.filter(function(d) {
                    if(d.attributes && d.attributes.name == itemData.name) {
                        return true;
                    }
                    return false;
                  });
                if(jsonFiles.length == 0) {
                    var message = 'Error: Something went wrong when retrieving item.';
                    _showError(tb, message);
                    $('.weko-button-publish i').attr('class', 'fa fa-upload');
                }else{
                    _processPublish(tb, parentItem, contextItem, jsonFiles[0].attributes);
                }
            },
            error: function(xhr, textStatus, errorThrown) {
                console.log('Error: ' + textStatus, errorThrown);
                var message = 'Error: Something went wrong when retrieving item. ' + textStatus;
                _showError(tb, message);
                $('.weko-button-publish i').attr('class', 'fa fa-upload');
            }});
    }else{
        _processPublish(tb, parentItem, contextItem, itemData);
    }
}

function _processPublish(tb, parentItem, contextItem, itemData) {
    console.log('publish', parentItem, itemData);
    $.getJSON(window.contextVars.node.urls.api + 'weko/serviceitemtype').done(function (data) {
        console.log('ServiceItemType loaded');
        $('.weko-button-publish i').attr('class', 'fa fa-upload');
        var fileDesc = {asWEKOExport: m.prop(false), serviceItemType: m.prop(0)};
        var modalContent = [m('.form-group', [
                               m('label', [
                                   m('input[type=checkbox]',
                                     {onchange: function() {
                                                    fileDesc.asWEKOExport(this.checked);
                                                    $('#service_item_type').prop('disabled', this.checked);
                                                },
                                      disabled: ! itemData.extra.has_import_xml}),
                                   'Import as WEKO EXPORT zip'
                                 ])
                              ]),
                            m('.form-group', [
                               m('label', 'Service item type'),
                               m('select.form-control#service_item_type',
                                  {onchange: m.withAttr('value', fileDesc.serviceItemType),
                                   disabled: fileDesc.asWEKOExport()},
                                  data.item_type.map(function(d, i){
                                      return m('option', { value: i, innerHTML: d.name });
                                  }))
                              ])];
        var modalActions = [m('button.btn.btn-default', {onclick: function () {
                                tb.modal.dismiss();
                                tb.updateFolder(null, parentItem);
                            }}, 'Cancel'),
                            m('button.btn.btn-primary', {onclick: function () {
                                $('.weko-button-publish i').attr('class', 'fa fa-spinner fa-pulse fa-3x fa-fw');
                                tb.modal.dismiss();
                                _submitDraft(tb,
                                             parentItem,
                                             contextItem,
                                             itemData,
                                             {asWEKOExport: fileDesc.asWEKOExport(),
                                              serviceItemType: fileDesc.serviceItemType()},
                                             function() {
                                                 $('.weko-button-publish i').attr('class', 'fa fa-upload');
                                                 tb.updateFolder(null, parentItem);
                                             });
                            }}, 'Submit')];
        tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', 'Select file type'));
    }).fail(function (xhr, status, error) {
        console.log('Error: ' + status, error);
        var message = 'Error: Something went wrong when retrieving serviceitemtype. ' + status;
        _showError(tb, message);
        $('.weko-button-publish i').attr('class', 'fa fa-upload');
    });
}
*/

function _uploadSuccess(file, item, response) {
    var tb = this;
    console.log('Uploaded', item, response);
    if(response.data.attributes.extra.archivable) {
        console.log('Publishing...', response);
        _publish(tb, _findItem(tb.treeData, item.parentID), item,
                 response.data.attributes);
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
