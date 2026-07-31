'use strict';
// Copy npm-managed assets that the mako templates serve as static files.
var fs = require('fs');
var path = require('path');

var targets = [
    ['node_modules/jquery/dist', 'website/static/vendor/npm/jquery/dist'],
    ['node_modules/components-jqueryui/jquery-ui.min.js', 'website/static/vendor/npm/components-jqueryui/jquery-ui.min.js'],
    ['node_modules/raven-js/dist', 'website/static/vendor/npm/raven-js/dist'],
    ['node_modules/mathjax', 'website/static/vendor/npm/mathjax'],
];

targets.forEach(function(pair) {
    var src = path.resolve(__dirname, pair[0]);
    var dest = path.resolve(__dirname, pair[1]);
    fs.rmSync(dest, {recursive: true, force: true});
    fs.mkdirSync(path.dirname(dest), {recursive: true});
    fs.cpSync(src, dest, {recursive: true});
});
