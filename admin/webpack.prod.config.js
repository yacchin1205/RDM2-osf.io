var webpack = require('webpack');
var admin = require('./webpack.admin.config.js');
var assign = require('object-assign');
var SaveAssetsJson = require('assets-webpack-plugin');
var TerserPlugin = require('terser-webpack-plugin');

var PUBLIC_PATH = '/static/public/js/';

module.exports = assign(admin, {
    mode: 'production',
    devtool: false,
    stats: {reasons: false},
    plugins: admin.plugins.concat([
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: JSON.stringify('production')
            },
            DEBUG: false,
            '__DEV__': false
        }),
        // Save a webpack-assets.json file that maps base filename to filename with
        // hash. This file is used by the webpack_asset mako filter to expand
        // base filenames to full filename with hash.
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
    output: Object.assign({}, admin.output, {
        publicPath: PUBLIC_PATH,
        // Append hash to filenames for cachebusting
        filename: '[name].[chunkhash].js',
    }),
});
