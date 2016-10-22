'use strict';

var swiftNodeConfig = require('./swiftNodeConfig.js').s3NodeConfig;

var url = window.contextVars.node.urls.api + 'niiswift/settings/';

new swiftNodeConfig('Amazon S3', '#swiftScope', url, '#swiftGrid');
