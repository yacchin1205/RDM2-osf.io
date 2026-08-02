'use strict';
// Copy npm-managed assets that the admin templates serve as static files.
var fs = require('fs');
var path = require('path');

var targets = [
    ['node_modules/jquery/dist', 'static/vendor/npm/jquery/dist'],
    ['node_modules/components-jqueryui/themes', 'static/vendor/npm/components-jqueryui/themes'],
    ['node_modules/components-jqueryui/jquery-ui.min.js', 'static/vendor/npm/components-jqueryui/jquery-ui.min.js'],
    ['node_modules/raven-js/dist', 'static/vendor/npm/raven-js/dist'],
    ['node_modules/bootstrap/dist', 'static/vendor/npm/bootstrap/dist'],
    ['node_modules/admin-lte/dist', 'static/vendor/npm/admin-lte/dist'],
];

targets.forEach(function(pair) {
    var src = path.resolve(__dirname, pair[0]);
    var dest = path.resolve(__dirname, pair[1]);
    fs.rmSync(dest, {recursive: true, force: true});
    fs.mkdirSync(path.dirname(dest), {recursive: true});
    fs.cpSync(src, dest, {recursive: true});
});
