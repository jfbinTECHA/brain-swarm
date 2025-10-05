#!/usr/bin/env python3
"""
Auto-generate OpenAPI documentation and MkDocs content for Brain Swarm
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

def generate_openapi_spec():
    """Generate OpenAPI specification from FastAPI app"""
    try:
        # Import the FastAPI app
        from api.main import app

        # Generate OpenAPI spec
        openapi_spec = app.openapi()

        # Ensure docs directory exists
        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)

        # Write OpenAPI spec
        with open("docs/openapi.json", "w") as f:
            json.dump(openapi_spec, f, indent=2, default=str)

        print("✅ Generated OpenAPI specification: docs/openapi.json")

        # Generate endpoint documentation
        generate_endpoint_docs(openapi_spec)

        return openapi_spec

    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        print("Make sure all dependencies are installed and the app can be imported")
        return None
    except Exception as e:
        print(f"❌ Failed to generate OpenAPI spec: {e}")
        return None

def generate_endpoint_docs(openapi_spec: Dict[str, Any]):
    """Generate detailed endpoint documentation from OpenAPI spec"""

    if not openapi_spec or "paths" not in openapi_spec:
        print("❌ No valid OpenAPI spec provided")
        return

    # Create API endpoints documentation
    endpoints_content = "# API Endpoints\n\n"
    endpoints_content += "Detailed documentation for all Brain Swarm API endpoints.\n\n"

    # Group endpoints by tags
    tagged_endpoints = {}

    for path, methods in openapi_spec["paths"].items():
        for method, spec in methods.items():
            if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue

            # Get tags
            tags = spec.get("tags", ["General"])
            tag = tags[0] if tags else "General"

            if tag not in tagged_endpoints:
                tagged_endpoints[tag] = []

            tagged_endpoints[tag].append({
                "path": path,
                "method": method.upper(),
                "spec": spec,
                "summary": spec.get("summary", ""),
                "description": spec.get("description", "")
            })

    # Generate documentation for each tag
    for tag, endpoints in tagged_endpoints.items():
        endpoints_content += f"## {tag}\n\n"

        for endpoint in sorted(endpoints, key=lambda x: (x["path"], x["method"])):
            endpoints_content += f"### {endpoint['method']} {endpoint['path']}\n\n"

            if endpoint["summary"]:
                endpoints_content += f"**{endpoint['summary']}**\n\n"

            if endpoint["description"]:
                endpoints_content += f"{endpoint['description']}\n\n"

            # Parameters
            if "parameters" in endpoint["spec"]:
                endpoints_content += "**Parameters:**\n\n"
                for param in endpoint["spec"]["parameters"]:
                    required = " (required)" if param.get("required", False) else ""
                    endpoints_content += f"- `{param['name']}` ({param.get('schema', {}).get('type', 'string')}){required}: {param.get('description', '')}\n"
                endpoints_content += "\n"

            # Request body
            if "requestBody" in endpoint["spec"]:
                endpoints_content += "**Request Body:**\n\n"
                content = endpoint["spec"]["requestBody"].get("content", {})
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    if "$ref" in schema:
                        # Resolve reference
                        ref = schema["$ref"].replace("#/components/schemas/", "")
                        if "components" in openapi_spec and "schemas" in openapi_spec["components"]:
                            schema = openapi_spec["components"]["schemas"].get(ref, {})

                    endpoints_content += "```json\n"
                    endpoints_content += json.dumps(generate_example_from_schema(schema), indent=2)
                    endpoints_content += "\n```\n\n"

            # Responses
            if "responses" in endpoint["spec"]:
                endpoints_content += "**Responses:**\n\n"
                for status_code, response_spec in endpoint["spec"]["responses"].items():
                    description = response_spec.get("description", "")
                    endpoints_content += f"- **{status_code}**: {description}\n"

                    # Response body example
                    if "content" in response_spec:
                        content = response_spec["content"]
                        if "application/json" in content:
                            schema = content["application/json"].get("schema", {})
                            if "$ref" in schema:
                                ref = schema["$ref"].replace("#/components/schemas/", "")
                                if "components" in openapi_spec and "schemas" in openapi_spec["components"]:
                                    schema = openapi_spec["components"]["schemas"].get(ref, {})

                            endpoints_content += "\n```json\n"
                            endpoints_content += json.dumps(generate_example_from_schema(schema), indent=2)
                            endpoints_content += "\n```\n"

                endpoints_content += "\n"

            endpoints_content += "---\n\n"

    # Write endpoints documentation
    with open("docs/api/endpoints.md", "w") as f:
        f.write(endpoints_content)

    print("✅ Generated endpoint documentation: docs/api/endpoints.md")

    # Generate models documentation
    generate_models_docs(openapi_spec)

def generate_models_docs(openapi_spec: Dict[str, Any]):
    """Generate API models documentation"""

    if not openapi_spec or "components" not in openapi_spec or "schemas" not in openapi_spec["components"]:
        return

    models_content = "# API Models\n\n"
    models_content += "Data models used by the Brain Swarm API.\n\n"

    schemas = openapi_spec["components"]["schemas"]

    for model_name, schema in schemas.items():
        models_content += f"## {model_name}\n\n"

        if "description" in schema:
            models_content += f"{schema['description']}\n\n"

        # Properties
        if "properties" in schema:
            models_content += "**Properties:**\n\n"
            required = schema.get("required", [])

            for prop_name, prop_spec in schema["properties"].items():
                prop_type = prop_spec.get("type", "object")
                if "items" in prop_spec:
                    prop_type = f"array of {prop_spec['items'].get('type', 'object')}"

                required_mark = " (required)" if prop_name in required else ""
                description = prop_spec.get("description", "")

                models_content += f"- `{prop_name}` ({prop_type}){required_mark}: {description}\n"

            models_content += "\n"

        # Example
        example = generate_example_from_schema(schema)
        if example:
            models_content += "**Example:**\n\n```json\n"
            models_content += json.dumps(example, indent=2)
            models_content += "\n```\n\n"

        models_content += "---\n\n"

    # Write models documentation
    with open("docs/api/models.md", "w") as f:
        f.write(models_content)

    print("✅ Generated models documentation: docs/api/models.md")

def generate_example_from_schema(schema: Dict[str, Any]) -> Any:
    """Generate an example from JSON schema"""
    if not schema:
        return None

    schema_type = schema.get("type")

    if schema_type == "object":
        example = {}
        properties = schema.get("properties", {})
        for prop_name, prop_spec in properties.items():
            example[prop_name] = generate_example_from_schema(prop_spec)
        return example

    elif schema_type == "array":
        items_schema = schema.get("items", {})
        return [generate_example_from_schema(items_schema)]

    elif schema_type == "string":
        examples = schema.get("examples", [])
        if examples:
            return examples[0]

        enum = schema.get("enum")
        if enum:
            return enum[0]

        format_type = schema.get("format")
        if format_type == "date-time":
            return "2023-01-01T12:00:00Z"
        elif format_type == "email":
            return "user@example.com"
        elif format_type == "uuid":
            return "550e8400-e29b-41d4-a716-446655440000"
        else:
            return "string"

    elif schema_type == "integer":
        return schema.get("default", 42)

    elif schema_type == "number":
        return schema.get("default", 3.14)

    elif schema_type == "boolean":
        return schema.get("default", True)

    else:
        # Handle $ref
        if "$ref" in schema:
            return f"Reference to {schema['$ref']}"

        return "example_value"

def update_mkdocs_nav():
    """Update MkDocs navigation with generated content"""
    # This would update mkdocs.yml if needed
    pass

def main():
    """Main documentation generation function"""
    print("🚀 Generating Brain Swarm API Documentation...")
    print()

    # Generate OpenAPI spec and docs
    openapi_spec = generate_openapi_spec()

    if openapi_spec:
        print()
        print("📊 Documentation Summary:")
        print(f"  - OpenAPI spec: docs/openapi.json")
        print(f"  - Endpoints: docs/api/endpoints.md")
        print(f"  - Models: docs/api/models.md")
        print()
        print("🎉 Documentation generation complete!")
        print()
        print("To serve the documentation locally:")
        print("  pip install mkdocs mkdocs-material")
        print("  mkdocs serve")
        print()
        print("To build static site:")
        print("  mkdocs build")
    else:
        print("❌ Documentation generation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()