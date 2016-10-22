var S3UserConfig = require('./swiftUserConfig.js').S3UserConfig;

// Endpoint for S3 user settings
var url = '/api/v1/settings/niiswift/accounts/';

var swiftUserConfig = new S3UserConfig('#swiftAddonScope', url);
