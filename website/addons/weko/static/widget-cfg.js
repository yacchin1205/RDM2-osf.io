var DataverseWidget = require('./wekoWidget.js');

var url = window.contextVars.node.urls.api + 'weko/widget/contents/';
// #dataverseScope will only be in the DOM if the addon is properly configured
if ($('#dataverseScope')[0]) {
    new DataverseWidget('#dataverseScope', url);
}
