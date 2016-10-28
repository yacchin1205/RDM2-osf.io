var WEKOWidget = require('./wekoWidget.js');

var url = window.contextVars.node.urls.api + 'weko/widget/contents/';
// #wekoScope will only be in the DOM if the addon is properly configured
if ($('#wekoScope')[0]) {
    new WEKOWidget('#wekoScope', url);
}
