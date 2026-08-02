'use strict';

var $ = require('jquery');
var MathJax = require('MathJax');

/**
 * Render math with MathJax within a given element.
 * */
function mathjaxify(selector) {
    var elements = $(selector).toArray();
    if (typeof(window.typeset) === 'undefined' || window.typeset === true) {
        // MathJax 3: wait for startup before the first typeset
        MathJax.startup.promise.then(function() {
            return MathJax.typesetPromise(elements);
        });
    }
}


module.exports = {
    mathjaxify: mathjaxify
};
