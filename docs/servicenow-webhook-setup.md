# ServiceNow Webhook Configuration for BrainSwarmOps

This guide explains how to configure ServiceNow to send real-time webhook notifications to BrainSwarmOps when incidents are resolved or closed.

## Prerequisites

- ServiceNow Personal Developer Instance (PDI) or production instance
- Admin access to configure REST messages and business rules
- BrainSwarmOps deployed and accessible

## Method 1: Outbound REST Message

### Step 1: Create REST Message

1. Navigate to **System Web Services > Outbound > REST Message**
2. Click **New**
3. Configure:
   - **Name**: `BrainSwarmOps Incident Webhook`
   - **Endpoint**: `https://swarmops-hook.brainswarm.svc.cluster.local/servicenow-webhook`
   - **Authentication Type**: `No authentication` (or configure as needed)

### Step 2: Add HTTP Method

1. In the REST Message record, go to **HTTP Methods** tab
2. Click **New**
3. Configure:
   - **HTTP Method**: `POST`
   - **Endpoint**: `https://swarmops-hook.brainswarm.svc.cluster.local/servicenow-webhook`
   - **Content-Type**: `application/json`

### Step 3: Create HTTP Request

1. In the HTTP Method record, go to **HTTP Request** tab
2. Click **New**
3. Configure the request body (JSON payload):

```json
{
  "result": {
    "sys_id": "${sys_id}",
    "number": "${number}",
    "state": "${state}",
    "short_description": "${short_description}",
    "caller_id": "${caller_id}",
    "assigned_to": "${assigned_to}",
    "resolved_at": "${resolved_at}",
    "closed_at": "${closed_at}"
  }
}
```

## Method 2: Flow Designer (Recommended)

### Step 1: Create New Flow

1. Navigate to **Flow Designer > Flows**
2. Click **New**
3. Configure:
   - **Name**: `Incident Resolution Webhook`
   - **Description**: `Send webhook when incident is resolved or closed`
   - **Trigger**: `Record`

### Step 2: Configure Trigger

1. In the Flow, select the trigger
2. Configure:
   - **Table**: `Incident [incident]`
   - **Trigger Conditions**:
     - **When to run**: `Before Record Update`
     - **Filter Conditions**:
       - `State` `changes to` `Resolved`
       - OR `State` `changes to` `Closed`
       - OR `State` `changes` (to capture all state changes)

### Step 3: Add REST Step

1. Add a **REST** step to the flow
2. Configure:
   - **Connection**: Create new connection or use existing
     - **Connection URL**: `https://swarmops-hook.brainswarm.svc.cluster.local`
     - **Authentication**: None (or configure as needed)
   - **Method**: `POST`
   - **Endpoint**: `/servicenow-webhook`
   - **Headers**:
     - `Content-Type`: `application/json`
   - **Request Body**:

```json
{
  "result": {
    "sys_id": "${record.sys_id}",
    "number": "${record.number}",
    "state": "${record.state}",
    "short_description": "${record.short_description}",
    "caller_id": "${record.caller_id.display_value}",
    "assigned_to": "${record.assigned_to.display_value}",
    "resolved_at": "${record.resolved_at}",
    "closed_at": "${record.closed_at}",
    "updated_on": "${record.sys_updated_on}"
  }
}
```

### Step 4: Add Error Handling

1. Add error handling to the REST step
2. Configure to log errors but not fail the incident update

## Method 3: Business Rule

### Step 1: Create Business Rule

1. Navigate to **System Definition > Business Rules**
2. Click **New**
3. Configure:
   - **Name**: `BrainSwarmOps Incident Webhook`
   - **Table**: `Incident [incident]`
   - **Active**: `true`
   - **When to run**:
     - **When**: `before`
     - **Update**: `true`
     - **Filter Conditions**: `State` `changes to` `7` (Resolved) OR `State` `changes to` `8` (Closed)

### Step 2: Add Script

1. In the **Advanced** tab, add this script:

```javascript
(function executeRule(current, previous) {
    try {
        var request = new sn_ws.RESTMessageV2();
        request.setEndpoint('https://swarmops-hook.brainswarm.svc.cluster.local/servicenow-webhook');
        request.setHttpMethod('post');
        request.setRequestHeader('Content-Type', 'application/json');

        var payload = {
            "result": {
                "sys_id": current.sys_id,
                "number": current.number,
                "state": current.state,
                "short_description": current.short_description,
                "caller_id": current.caller_id.getDisplayValue(),
                "assigned_to": current.assigned_to ? current.assigned_to.getDisplayValue() : "",
                "resolved_at": current.resolved_at,
                "closed_at": current.closed_at,
                "updated_on": current.sys_updated_on
            }
        };

        request.setRequestBody(JSON.stringify(payload));

        var response = request.execute();
        var httpResponseStatus = response.getStatusCode();
        var httpResponseContent = response.getBody();

        if (httpResponseStatus != 200) {
            gs.error('BrainSwarmOps webhook failed: ' + httpResponseStatus + ' - ' + httpResponseContent);
        } else {
            gs.info('BrainSwarmOps webhook sent for incident: ' + current.number);
        }

    } catch (ex) {
        gs.error('BrainSwarmOps webhook error: ' + ex.message);
    }
})(current, previous);
```

## Testing the Configuration

### Test Incident Creation

1. Create a test incident in ServiceNow
2. Verify it appears in BrainSwarmOps dashboard

### Test Resolution Webhook

1. Resolve or close the test incident
2. Check that the webhook fires (check ServiceNow logs)
3. Verify the incident shows as resolved in BrainSwarmOps dashboard
4. Confirm green resolution marker appears on Grafana graphs

## Troubleshooting

### Webhook Not Firing

- Check Business Rule/Flow is active
- Verify trigger conditions match incident state changes
- Check ServiceNow system logs for errors

### Webhook Request Failing

- Verify the webhook URL is accessible from ServiceNow
- Check authentication if configured
- Review BrainSwarmOps logs for request processing errors

### Incident Not Marked as Resolved

- Verify the incident number format matches between systems
- Check that the webhook payload contains required fields
- Review BrainSwarmOps logs for processing errors

## Security Considerations

- Consider implementing authentication for webhook endpoints
- Use HTTPS for all webhook communications
- Validate webhook payloads to prevent malicious requests
- Monitor webhook usage and implement rate limiting if needed

## Alternative: Scheduled Polling

If webhooks are not feasible, the system also supports scheduled polling via the `swarmops_ticket_sync.py` CronJob, which runs every 10 minutes to check for resolved incidents.