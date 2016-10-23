var DataverseNodeConfig = require('./wekoNodeConfig.js');

var url = window.contextVars.node.urls.api + 'weko/settings/';
new DataverseNodeConfig('#wekoScope', url);
