/**
* Module that enables account claiming on the project page. Makes unclaimed
* usernames show popovers when clicked, where they can input their email.
*
* Sends HTTP requests to the claim_user_post endpoint.
*/
'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

var currentUserId = window.contextVars.currentUser.id;

function AccountClaimer (selector) {
    this.selector = selector;
    this.element = $(selector);  // Should select all span elements for
                                // unreg contributor names
    this.init();
}

function getClaimUrl() {
    var uid = $(this).data('pk');
    var pid = global.nodeId;
    var viewOnlyToken = $osf.urlParams().view_only;
    return '/api/v1/user/' + uid + '/' + pid +  '/claim/email/' + (viewOnlyToken ? '?view_only=' + viewOnlyToken : '');
}

function alertFinished(email) {
    $osf.growl(_('Email will arrive shortly'), [_('Please check <em>'), $osf.htmlEscape(email), '</em>'].join(''), 'success');
}

function onClickIfLoggedIn() {
    var pk = $(this).data('pk');
    if (pk !== currentUserId) {
        bootbox.confirm({
            title: sprintf(_('Claim as %1$s?'),$osf.htmlEscape(global.contextVars.currentUser.username)),
            message: _('If you claim this account, a contributor of this project ') +
                    _('will be emailed to confirm your identity.'),
            callback: function(confirmed) {
                if (confirmed) {
                    $osf.postJSON(
                        getClaimUrl(),
                        {
                            claimerId: currentUserId,
                            pk: pk
                        }
                    ).done(function(response) {
                        alertFinished(response.email);
                    }).fail(
                        $osf.handleJSONError
                    );
                }
            },
            buttons:{
                confirm:{
                    label:_('Claim')
                }
            }
        });
    }
}

AccountClaimer.prototype = {
    constructor: AccountClaimer,
    init: function() {
        var self = this;
        self.element.tooltip({
            title: _('Is this you? Click to claim')
        });
        if (currentUserId.length) { // If user is logged in, ask for confirmation
            self.element.on('click', onClickIfLoggedIn);
        } else {
            self.element.editable({
                type: 'text',
                value: '',
                ajaxOptions: {
                    type: 'post',
                    contentType: 'application/json',
                    dataType: 'json'  // Expect JSON response
                },
                success: function(data) {
                    alertFinished(data.email);
                },
                error: $osf.handleJSONError,
                display: function(value, sourceData){
                    if (sourceData && sourceData.fullname) {
                        $(this).text(sourceData.fullname);
                    }
                },
                // Send JSON payload
                params: function(params) {
                    return JSON.stringify(params);
                },
                title: _('Claim Account'),
                placement: 'bottom',
                placeholder: _('Enter email...'),
                validate: function(value) {
                    var trimmed = $.trim(value);
                    if (!$osf.isEmail(trimmed)) {
                        return _('Not a valid email.');
                    }
                },
                url: getClaimUrl.call(this),
            });
        }
    }
};

module.exports = AccountClaimer;
