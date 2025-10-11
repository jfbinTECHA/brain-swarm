# OpenAPI Specification

This page contains the OpenAPI specification for the Brain Swarm Federation API.

## Federation Operations Server API

::: render_swagger
path: ../federation_openapi.yaml
:::

## Alternative Usage

You can also embed OpenAPI specs directly:

```yaml
openapi: 3.0.3
info:
  title: Brain Swarm Federation API
  version: 1.0.0
  description: API for managing swarm federation operations
paths:
  /health:
    get:
      summary: Health check endpoint
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: healthy
                  timestamp:
                    type: number
                    example: 1640995200.0
```

## API Endpoints Summary

- **GET /health** - Service health check
- **GET /stats** - System statistics (authenticated)
- **GET /mode** - Current operation mode
- **POST /mode** - Switch operation mode (admin only)
- **WebSocket /socket.io/** - Real-time updates

For detailed API documentation, see the [API Reference](../api-reference.md) page.