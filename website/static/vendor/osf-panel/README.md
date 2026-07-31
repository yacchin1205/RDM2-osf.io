# osf-panel
Smart panels that show and hide bootstrap columns

### How to Install

If you are using Bower, add osf-panel to your bower.json file and install by running

```bower install osf-panel```

If you just want to use the distribution file, copy paste dist/jquery-osfPanel.js or the minified version to your project.


### How to use it

Step 1: You need to create a div tag that will include the buttons. Add a class to this div that you can pass to the plugin.

```html
<div class="switch pull-right"></div>
```

Step 2: Then for each of the columns you want to use add the title you would like to appear on the button. This will also initialize the plugin for these columns. If you don't add this to a column it will not be included in the toggle.

```html
    <div class="col-md-5" data-osf-panel="Second">
    ...
    </div>
```

Step 3: Initialize the plugin with javascript. Here you can add options. The most important one is the selector that identifies where the button div is.

```html
<script type="text/javascript">
    $(document).ready(function(){
        $('*[data-osf-panel]').osfPanel({ buttonElement : '.switch', onSize : 'md' });
    });
</script>
```

After the plugin initializes your column will have some data attributes added (You should not add them yourself, this is for reference): 
```html
<div data-osf-panel="View" class="col-md-6 col-sm-6 col-xs-12" data-osf-toggle="on" data-initial-state="on" data-css-cache="col-sm-6">
…
</div>
```
- **data-osf-toggle="on"** : Shows the current state, it will be 'on' or off
- **data-initial-state="on"** : A cache for what the initial state was in case of adjusting visibility when reset. 
- **data-css-cache=""** : A cache for other sizing classes so that when reset they go back to original classes.


### Options

Here's a description of options:

```javascript
    var settings = {                                       // Default options
        complete : null,                                            // Function to run at the end.
        sizes : { "xs" : 0, "sm" : 768, "md" : 992, "lg" : 1200 },  // Default Bootstrap sizes. If you edited your default sizes change them here as well
        buttonElement : ".switch",                                  // Where to place the buttons
        onClass : 'btn-primary',                                    // The class to add to buttons for ON
        offClass : 'btn-default',                                   // The class to add to buttons for OFF
        onSize : 'sm'                                               // Which size onwards to apply, it's best to start at sm.
        onclick : null                                              // Functio to run when a toggle button is clicked
    };
```

### onclick()

The onclick hook adds the ability to run your own functions when a user clicks on one of the toggle buttons. 
Onclick hs the following arguments
```javascript
    onclick(event, label, buttonState, item, column);
```

| Variable | Value |
| ------------- | ------------- |
| this  | is set to the jquery list of columns that are affected by the plugin. | 
| event  | Browser click event | 
| label  | The text of the button as passed in by the data-osf-panel  | 
| item  | the single $(element) jquery item for the button | 
| column  | the single $(element) jquery item for the column | 


### How to add fixed width columns

There are potential scenarios where you need to keep a column a certain size despite the toggle state. For instance you might have a sidebar that needs to be 2 columns wide when visible regardless of what other columns are visible in the grid. For these cases you can hard code the column sizes. osf-panel will stick to these sizes when resizing and expand others to fill the blanks. The demo uses two of these. As with all grids you need to make sure that your numbers make sense and add up to 12. 

```html
    <div class="col-md-5" data-osf-panel="Second" data-osf-panel-col="3">
    ...
    </div>
```
