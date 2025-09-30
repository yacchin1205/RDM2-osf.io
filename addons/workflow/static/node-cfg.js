const WorkflowNodeConfig = require('./workflowNodeConfig.js');

const SHORT_NAME = 'workflow';
const nodeId = window.contextVars.node.id;
const registrationsUrl = window.contextVars.node.urls.api + SHORT_NAME + '/registrations/';
const enginesUrl = window.contextVars.node.urls.api + SHORT_NAME + '/engines/';

new WorkflowNodeConfig('#' + SHORT_NAME + 'Scope', {
    nodeId,
    registrationsUrl,
    enginesUrl,
});
