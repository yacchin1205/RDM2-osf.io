'use strict';

var swiftNodeConfig = require('./swiftNodeConfig.js').swiftNodeConfig;

var url = window.contextVars.node.urls.api + 'swift/settings/';

new swiftNodeConfig('NII Swift', '#swiftScope', url, '#swiftGrid');
