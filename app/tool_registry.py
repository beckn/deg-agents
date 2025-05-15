from typing import Callable, Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def create_dynamic_tool_function(
    endpoint_info: Dict[str, Any],
) -> Callable[..., Dict[str, Any]]:
    """
    Dynamically creates a placeholder function for an API endpoint.
    This function will log its invocation and expected parameters.
    """

    def tool_function(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        # Construct a unique tool name for logging/identification
        tool_name = f"{endpoint_info['spec_name']}_{endpoint_info['operation_id']}"

        log_message = (
            f"Tool '{tool_name}' (Endpoint: {endpoint_info['method']} {endpoint_info['path']}) "
            f"would be called with:"
        )

        # Log positional arguments (if any were designed for the tool)
        if args:
            log_message += f"\n  Positional Args: {args}"

        # Log keyword arguments (more likely for API parameters)
        if kwargs:
            log_message += "\n  Keyword Args:"
            for key, value in kwargs.items():
                log_message += f"\n    {key}: {value}"

        # Placeholder for actual API call logic
        # For now, just simulate a response
        simulated_response = {
            "status": "success",
            "message": f"Tool '{tool_name}' simulated execution.",
            "endpoint_info": {
                "method": endpoint_info["method"],
                "path": endpoint_info["path"],
                "summary": endpoint_info["summary"],
                "base_url_template": endpoint_info["base_url_template"],
            },
            "received_args": args,
            "received_kwargs": kwargs,
        }

        logger.info(log_message)
        print(log_message)  # Also print to console for visibility during dev
        print(f"Simulated response for {tool_name}: {simulated_response}")

        return simulated_response

    # Set a descriptive name for the dynamic function for easier debugging
    tool_function.__name__ = (
        f"tool_{endpoint_info['spec_name']}_{endpoint_info['operation_id']}"
    )
    tool_function.__doc__ = (
        f"Dynamically generated tool for {endpoint_info['spec_name']} API: "
        f"{endpoint_info['summary']} ({endpoint_info['method']} {endpoint_info['path']}).\n"
        f"Expected parameters (based on OpenAPI spec): {endpoint_info['parameters']}\n"
        f"Request body schema (based on OpenAPI spec): {endpoint_info['request_body_schema']}"
    )
    return tool_function


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable[..., Dict[str, Any]]] = {}
        self.tool_descriptions: Dict[str, str] = {}

    def register_tool(self, endpoint_info: Dict[str, Any]):
        """
        Creates and registers a tool function based on endpoint_info.
        The tool name will be unique, typically based on spec_name and operationId.
        """
        # Create a unique and somewhat descriptive tool name
        # Prioritize operationId if available and seems reasonably unique
        # Fallback to method and path if operationId is generic or missing

        base_name = endpoint_info["operation_id"]
        if not base_name or base_name.startswith(
            f"{endpoint_info['spec_name']}_"
        ):  # if it's a generated one
            # Sanitize path for use in function name
            sanitized_path = (
                endpoint_info["path"]
                .replace("/", "_")
                .replace("{", "")
                .replace("}", "")
                .strip("_")
            )
            base_name = f"{endpoint_info['method'].lower()}_{sanitized_path}"

        tool_name = f"{endpoint_info['spec_name']}_{base_name}"

        # Ensure uniqueness if multiple specs might somehow produce clashing names (unlikely with spec_name prefix)
        counter = 0
        original_tool_name = tool_name
        while tool_name in self.tools:
            counter += 1
            tool_name = f"{original_tool_name}_{counter}"

        tool_function = create_dynamic_tool_function(endpoint_info)
        self.tools[tool_name] = tool_function

        # Store a description for the agent to potentially use
        description = (
            f"Tool Name: {tool_name}\n"
            f"API: {endpoint_info['spec_name']}\n"
            f"Operation: {endpoint_info['summary']} ({endpoint_info['method']} {endpoint_info['path']})\n"
            f"Description: {tool_function.__doc__}"  # Use the docstring of the generated function
        )
        self.tool_descriptions[tool_name] = description
        logger.info(
            f"Registered tool: {tool_name} for {endpoint_info['method']} {endpoint_info['path']}"
        )

    def get_tool(self, name: str) -> Optional[Callable[..., Dict[str, Any]]]:
        return self.tools.get(name)

    def get_all_tools(self) -> Dict[str, Callable[..., Dict[str, Any]]]:
        return self.tools

    def get_tool_descriptions(self) -> List[str]:
        return list(self.tool_descriptions.values())
