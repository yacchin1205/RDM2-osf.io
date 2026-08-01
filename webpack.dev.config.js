var common = require('./webpack.common.config.js');
var assign = require('object-assign');

module.exports = assign(common, {
    mode: 'development'
});
