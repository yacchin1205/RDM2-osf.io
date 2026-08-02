/**
 * osf-panel - Smart panels that show and hide bootstrap columns
 * @author Caner Uguz
 * @version v0.3.1
 * @link https://github.com/caneruguz/osf-panel
 * @license Apache 2.0
 */
/*jslint browser: true*/
(function ($) {
    'use strict';
    $.fn.osfPanel = function (options) {
        var settings = $.extend({                                       // Default options
            complete : null,                                            // Function to run at the end.
            sizes : { "xs" : 0, "sm" : 768, "md" : 992, "lg" : 1200 },  // Default Bootstrap sizes.
            buttonElement : ".switch",                                  // Where to place the buttons
            onClass : 'btn-primary',                                    // The class to add to buttons for ON
            offClass : 'btn-default',                                   // The class to add to buttons for OFF
            onSize : 'sm',                                               // Which size onwards to apply
            onclick : null                                              // onclick function hook
        }, options),
            el = this,                                                      // The elements this was called on. This is a list, should run .each().
            modes = ['xs', 'sm', 'md', 'lg'],
            size = settings.sizes,
            currentMode;
        // Check what size we are on
        el.updateMode = function () {
            var width = $(window).width();
            if (width >= size.xs && width < size.sm) {
                currentMode = "xs";
            }
            if (width >= size.sm && width < size.md) {
                currentMode = "sm";
            }
            if (width >= size.md && width < size.lg) {
                currentMode = "md";
            }
            if (width >= size.lg) {
                currentMode = "lg";
            }
        };
        // Adjust the widths of the visible columns
        el.adjustVisible = function () {
            var open = $('[data-osf-panel]:visible').length,
                fixedSizes = [],
                fixedSizeTotals = 0,
                openFixed = 0,
                fixedSizeExists = false,
                colsize,
                cssStrings,
                remainder,
                nonFixedCount,
                remainderEach,
                remainderTaken,
                leftOver,
                each,
                colCSS;
            el.each(function (index, element) {
                var $el = $(element),
                    i;
                colsize  = $el.attr('data-osf-panel-col');
                fixedSizes[index] = colsize;
                if (colsize && $el.css('display') !== 'none') {
                    fixedSizeExists = true;
                    fixedSizeTotals += parseInt(colsize, 10);
                    openFixed = openFixed + 1;
                }
                //remove pertinent css
                cssStrings = $el.attr('class').split(' ');
                for (i = 0; i < cssStrings.length; i += 1) {
                    if (cssStrings[i].indexOf('col-' + currentMode + '-') > -1) {
                        cssStrings.splice(i, 1);
                    }
                }
                $el.attr('class', cssStrings.join(' '));
            });
            // if mode is xs ignore sizes
            if(currentMode === 'xs'){
                el.each(function (index, element) {
                    $(element).addClass('col-xs-12');
                });
            } else {
                if (fixedSizeExists) {
                    remainder = 12 - fixedSizeTotals;
                    nonFixedCount = open - openFixed;
                    remainderEach = Math.floor(remainder / nonFixedCount);
                    remainderTaken = false;
                    el.each(function (index, element) {
                        var $el = $(element);
                        if (fixedSizes[index]) {
                            $el.addClass('col-' + currentMode + '-' + fixedSizes[index]);
                        } else {
                            // if this item is the last of the visible nonfixed and there is a remainder
                            leftOver = remainder - (remainderEach * nonFixedCount);
                            if (leftOver > 0 && !remainderTaken) {
                                $el.addClass('col-' + currentMode + '-' + (remainderEach + leftOver));
                                remainderTaken = true;
                            } else {
                                $el.addClass('col-' + currentMode + '-' + remainderEach);
                            }
                        }
                    });
                } else {
                    each = 12 / open;
                    colCSS = 'col-' + currentMode + '-' + each;
                    el.each(function (index, element) {
                        $(element).addClass(colCSS);
                    });
                }
            }

        };
        // Set some variables in the very beginning for consistency
        el.initialize = function () {
            el.each(function (index, element) {
                var $el = $(element),
                    css  =  $el.attr('class'),
                    cssStrings,
                    i;
                if(css){
                    cssStrings = css.split(' ');
                } else {
                    cssStrings = [];
                }
                if ($el.is(':visible')) {
                    $el.attr('data-osf-toggle', 'on');
                    $el.attr('data-initial-state', 'on');
                } else {
                    $el.attr('data-initial-state', 'off');
                    $el.attr('data-osf-toggle', 'off');
                }
                $el.attr('data-css-cache', $el.attr('class'));
                //remove all size related classes
                for (i = 0; i < cssStrings.length; i += 1) {
                    if (cssStrings[i].match(/(col-xs-|col-sm-|col-md-|col-lg)/)) {
                        cssStrings[i] = '';
                    }
                }
                $el.attr('class', cssStrings.join(' '));
            });
            el.createButtons();
        };
        // Clean up the changes this plugin does.
        el.reset = function () {
            $('[data-osf-panel]').each(function (index, element) {
                var $el = $(element);
                var cache = $el.attr('data-css-cache');
                var initialState = $el.attr('data-initial-state');
                if (initialState === 'on') {
                    $el.show();
                } else {
                    $el.hide();
                }
                if (cache && cache.length > 0) {
                    $el.attr('class', cache);
                }
            });
        };
        // Create the buttons
        el.createButtons = function () {
            el.updateMode();
            var $buttons = $(settings.buttonElement),
                $buttonGroup;
            $buttons.html('');
            if (modes.indexOf(currentMode) >= modes.indexOf(settings.onSize)) {
                $buttons.append('<div class="btn-group btn-group-sm"></div>');
                $buttonGroup = $(settings.buttonElement + ' > .btn-group');
                $buttonGroup.append('<div class="btn btn-default disabled">Toggle view: </div>');
                el.each(function (index, element) {
                    var $el = $(element),
                        btnClass = settings.offClass,
                        title = $el.attr('data-osf-panel'),
                        status = $el.attr('data-osf-toggle');
                    if (status === 'on') {
                        btnClass = settings.onClass;
                        $el.show();
                    }
                    if (status === 'off') {
                        btnClass = settings.offClass;
                        $el.hide();
                    }
                    $buttonGroup.append('<div class="btn ' + btnClass + '">' + title + '</div>');
                });
                el.adjustVisible();
            } else {
                el.reset();
            }
        };
        // Button on click
        $(document).on('click', settings.buttonElement + ' .btn', function (event) {
            var $this = $(this),
                title = $this.text(),
                $col = $('[data-osf-panel="' + title + '"]'),
                buttonState;
            if ($this.hasClass(settings.onClass)) {
                $this.removeClass(settings.onClass).addClass(settings.offClass);
                $col.attr('data-osf-toggle', 'off').hide();
            } else if ($this.hasClass(settings.offClass)) {
                $this.removeClass(settings.offClass).addClass(settings.onClass);
                $col.attr('data-osf-toggle', 'on').show();
            }
            el.adjustVisible();
            buttonState =  $col.attr('data-osf-toggle') === 'on' ? true : false;
            if ($.isFunction(settings.onclick)) {
                settings.onclick.call(el, event, title, buttonState, $this, $col);
            }
        });
        $(window).resize(function () {
            el.createButtons();
        });
        el.initialize();
        // Run the complete function if there is one
        if ($.isFunction(settings.complete)) {
            settings.complete.call(this);
        }
        // Return the element so jquery can chain it
        return this;
    };
}(jQuery));