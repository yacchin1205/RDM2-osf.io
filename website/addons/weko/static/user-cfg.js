var $osf = require('js/osfHelpers');
var DataverseViewModel = require('./wekoUserConfig.js').DataverseViewModel;

// Endpoint for Dataverse user settings
var url = '/api/v1/settings/weko/';

var dataverseViewModel = new DataverseViewModel(url);
$osf.applyBindings(dataverseViewModel, '#wekoAddonScope');

// Load initial Dataverse data
dataverseViewModel.fetch();
