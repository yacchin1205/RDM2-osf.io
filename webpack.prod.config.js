var path = require('path');

var webpack = require('webpack');
var common = require('./webpack.common.config.js');
var assign = require('object-assign');
var SaveAssetsJson = require('assets-webpack-plugin');
var TerserPlugin = require('terser-webpack-plugin');

var PUBLIC_PATH = '/static/public/js/';

module.exports = assign(common, {
    mode: 'production',
    stats: {reasons: false},
    plugins: common.plugins.concat([
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: JSON.stringify('production')
            },
            DEBUG: false,
            '__DEV__': false
        }),
        // Save a webpack-assets.json file that maps base filename to filename with
        // hash. This file is used by the webpack_asset mako filter to expand
        // base filenames to full filename with hash. The flat {name: filename}
        // shape is the contract expected by website/util/paths.py.
        new SaveAssetsJson({
            processOutput: function(assets) {
                var flat = {};
                Object.keys(assets).forEach(function(name) {
                    flat[name] = assets[name].js.replace(PUBLIC_PATH, '');
                });
                return JSON.stringify(flat);
            }
        })
    ]),
    optimization: {
        minimize: true,
        minimizer: [
            new TerserPlugin({
                exclude: /conference.*?\.js$/,
                parallel: true
            })
        ]
    },
    output: {
        path: path.resolve(__dirname, 'website', 'static', 'public', 'js'),
        publicPath: PUBLIC_PATH,
        // Append hash to filenames for cachebusting
        filename: '[name].[chunkhash].js',
        sourcePrefix: ''
    }
});
