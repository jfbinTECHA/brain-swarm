# API Overview

The Brain Swarm API provides RESTful endpoints for managing and monitoring the swarm intelligence system.

## Base URL

```
http://localhost:8000
```

## Authentication

Most endpoints require authentication. Use JWT tokens obtained through the authentication system.

## Response Format

All responses are in JSON format with the following structure:

```json
{
  "status": "success|error",
  "data": {...},
  "message": "Optional message",
  "timestamp": 1234567890
}
```

## Error Handling

Errors follow HTTP status codes:

- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

Error responses include:

```json
{
  "detail": "Error description",
  "error_code": "ERROR_CODE"
}
```

## Rate Limiting

API endpoints are rate-limited. Check the `X-RateLimit-*` headers in responses.

## Versioning

The API uses URL versioning: `/v1/endpoint`

## WebSocket Support

Real-time features use WebSocket connections at `/ws/*` endpoints.