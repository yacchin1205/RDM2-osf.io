# Workflow Addon

## Notification Endpoint

Workflow engines send notifications to RDM users via email, project comments, and NodeLog:

```
POST /api/v1/project/<pid>/workflow/engines/<engine_id>/runs/<process_instance_id>/notifications/
```

Requires Personal Access Token in Authorization header.

### Request Body

```json
{
  "title": "Task assigned",
  "body": [
    {
      "type": "text/plain",
      "content": "Please review the document"
    },
    {
      "type": "text/html",
      "content": "<p>Please review the document</p>"
    }
  ],
  "assignees": ["executor", "manager"],
  "send_email": true,
  "add_comment": false
}
```

- `title` (required): Notification title
- `body` (required): Array of body content with `type` and `content` fields
  - `text/plain` (required): Plain text content for NodeLog and comments
  - `text/html` (optional): HTML content for email display
- `assignees`: Role-based assignees - `"executor"`, `"manager"`, `"creator"`, `"contributor"`
- `user_ids`: Specific OSF user IDs
- `send_email`: Send email (default: false)
- `add_comment`: Add as project comment (default: false)

### Assignee Resolution

- `executor`: User who started the run (from `_RDM_WORKFLOW_METADATA.started_by`)
- `manager`: User who activated the workflow on this project
- `creator`: User who created the workflow registration
- `contributor`: All project contributors

### Response

```json
{
  "message": "Notification sent",
  "recipients": ["user1_id", "user2_id"]
}
```

### NodeLog Action

Notifications are logged with action type: `workflow_notification`

## Flowable Http Task Example

To send a notification from a Flowable workflow, use an Http Task with the following configuration:

```json
{
  "url": "${RDM_EXECUTOR_WEB_URL}/api/v1/project/${RDM_NODE_ID}/workflow/engines/${RDM_ENGINE_ID}/runs/${execution.processInstanceId}/notifications/",
  "httpMethod": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "requestBody": {
    "title": "Task assigned",
    "body": [
      {
        "type": "text/plain",
        "content": "Please review the document"
      },
      {
        "type": "text/html",
        "content": "<p>Please review the document</p>"
      }
    ],
    "assignees": ["executor", "manager"],
    "send_email": true,
    "add_comment": false
  }
}
```

**Variables used:**
- `${RDM_EXECUTOR_WEB_URL}` - Gateway proxy URL for executor token
- `${RDM_NODE_ID}` - Project ID
- `${RDM_ENGINE_ID}` - Engine ID
- `${execution.processInstanceId}` - Current process instance ID

**Important:** When registering the workflow, the Executor token must be set to "Use with Read permission" or "Use with ReadWrite permission". If set to "Do not use", the `RDM_EXECUTOR_WEB_URL` variable will not be available and the notification endpoint cannot be called.

You can also use `RDM_CREATOR_WEB_URL` or `RDM_MANAGER_WEB_URL` depending on which delegation token should be used for authentication.

**Note:** No `Authorization` header is needed - the Gateway automatically adds the delegation token.
