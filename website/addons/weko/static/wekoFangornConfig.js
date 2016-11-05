'use strict';

var m = require('mithril');
var URI = require('URIjs');
var $ = require('jquery');
var Raven = require('raven-js');

var Fangorn = require('js/fangorn');
var waterbutler = require('js/waterbutler');
var $osf = require('js/osfHelpers');

function changeState(grid, item, version) {
    item.data.version = version;
    grid.updateFolder(null, item);
}

function _downloadEvent(event, item, col) {
    event.stopPropagation();
    window.location = waterbutler.buildTreeBeardDownload(item, {path: item.data.extra.fileId});
}

// Define Fangorn Button Actions
var _wekoItemButtons = {
    view: function (ctrl, args, children) {
        var buttons = [];
        var tb = args.treebeard;
        var item = args.item;
        function _uploadEvent(event, item, col) {
            event.stopPropagation();
            tb.dropzone.hiddenFileInput.click();
            tb.dropzoneItemCache = item;
        }
        function registerItem(event, item, col) {
            console.log('Retrieving serviceitemtype...');
            console.log(item.data);
            $.getJSON(item.data.nodeApiUrl + 'weko/serviceitemtype').done(function (data) {
                console.log('ServiceItemType loaded');
                console.log(data);
                var modalContent = [m('p.m-md', 'Service item type'),
                                    m('select', {onchange: function(value){ console.log(value); }},
                                      data.item_type.map(function(d, i){
                                          return m('option', { value: i, innerHTML: d.name });
                                      }))];
                var modalActions = [m('button.btn.btn-default', {
                        'onclick': function () {
                            tb.modal.dismiss();
                        }
                    }, 'Cancel'),
                    m('button.btn.btn-primary', {
                        'onclick': function () {
                            publishDataset();
                        }
                    }, 'Next')];
                tb.modal.update(modalContent, modalActions, m('h3.break-word.modal-title', 'Select service item type'));
            }).fail(function (xhr, status, error) {
                    var statusCode = xhr.responseJSON.code;
                    var message = 'Error: Something went wrong when retrieving serviceitemtype. statusCode=' + statusCode;

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
                    tb.modal.update(modalContent, modalActions);
                });;
        }

        if (tb.options.placement !== 'fileview') {
            if (item.kind === 'folder') {
                buttons.push(m.component(Fangorn.Components.button, {
                                             onclick: function(event) {
                                                 registerItem.call(tb, event, item);
                                             },
                                             icon: 'fa fa-upload',
                                             className: 'text-success'
                                         }, 'Register Item'));
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            _uploadEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-upload',
                        className: 'text-success'
                    }, 'Upload')
                );
            } else if (item.kind === 'file') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            _downloadEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._removeEvent.call(tb, event, [item]);
                        },
                        icon: 'fa fa-trash',
                        className: 'text-danger'
                    }, 'Delete')
                );
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function(event) {
                            gotoFile(item);
                        },
                        icon: 'fa fa-external-link',
                        className : 'text-info'
                    }, 'View'));
            }
        }
        return m('span', buttons);
    }
};

function gotoFile (item) {
    var redir = new URI(item.data.nodeUrl);
    window.location = redir
        .segment('files')
        .segment(item.data.provider)
        .segment(item.data.extra.fileId)
        .query({version: item.data.extra.datasetVersion})
        .toString();
}

function _fangornColumns(item) {
    var tb = this;
    var columns = [];
    columns.push({
        data : 'name',
        folderIcons : true,
        filter : true
    });
    if (tb.options.placement === 'project-files') {
        columns.push(
        {
            data  : 'size',
            sortInclude : false,
            filter : false,
            custom : function() {return m('');}
        });
        columns.push(
        {
            data  : 'downloads',
            sortInclude : false,
            filter : false,
            custom : function() {return m('');}
        });
        columns.push({
            data: 'version',
            filter: false,
            sortInclude : false,
            custom: function() {return m('');}
        });
    }
    if(tb.options.placement !== 'fileview') {
        columns.push({
            data : 'modified',
            filter: false,
            custom : function() {return m('');}
        });
    }
    return columns;
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

function _fangornDeleteUrl(item) {
    return waterbutler.buildTreeBeardDelete(item, {full_path: item.data.path + '?' + $.param({name: item.data.name})});
}

function _fangornLazyLoad(item) {
    return waterbutler.buildTreeBeardMetadata(item, {version: item.data.version});
}

function _canDrop(item) {
    return true;
}

Fangorn.config.weko = {
    folderIcon: _fangornFolderIcons,
    resolveDeleteUrl: _fangornDeleteUrl,
    resolveRows: _fangornColumns,
    lazyload:_fangornLazyLoad,
    canDrop: _canDrop,
    itemButtons: _wekoItemButtons
};
