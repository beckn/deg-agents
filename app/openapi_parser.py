import json
from typing import Dict, List, Any, Optional


def load_openapi_spec(file_path: str) -> Dict[str, Any]:
    """Loads an OpenAPI specification from a JSON file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: OpenAPI spec file not found at {file_path}")
        raise
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        raise


def extract_endpoints_from_spec(
    spec: Dict[str, Any], spec_name: str
) -> List[Dict[str, Any]]:
    """
    Extracts endpoint information from a parsed OpenAPI specification.
    """
    endpoints = []
    if "paths" not in spec:
        print(f"Warning: 'paths' not found in spec: {spec_name}")
        return []

    # Determine base URL. Using the first server's URL as a default.
    # Actual base URL substitution for {{base_url}} will be handled by the tool/caller.
    base_url_template = ""
    if "servers" in spec and spec["servers"]:
        base_url_template = spec["servers"][0].get("url", "")

    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            # Common HTTP methods
            if method.lower() not in [
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "options",
                "head",
            ]:
                continue

            summary = operation.get("summary", "No summary")
            operation_id = operation.get(
                "operationId",
                f"{spec_name}_{method}_{path.replace('/', '_').strip('_')}",
            )

            parameters = operation.get("parameters", [])
            request_body_schema = None
            if "requestBody" in operation and "content" in operation["requestBody"]:
                # Taking the first content type, assuming JSON
                first_content_type = next(
                    iter(operation["requestBody"]["content"]), None
                )
                if first_content_type:
                    request_body_schema = operation["requestBody"]["content"][
                        first_content_type
                    ].get("schema")

            endpoints.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "summary": summary,
                    "operation_id": operation_id,
                    "parameters": parameters,
                    "request_body_schema": request_body_schema,
                    "base_url_template": base_url_template,  # Store the template
                    "spec_name": spec_name,
                }
            )
    return endpoints
