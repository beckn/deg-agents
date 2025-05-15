from typing import Dict, List, Any, Optional
from app.tool_registry import ToolRegistry
import logging
import google.generativeai as genai
from google.generativeai.types import (
    GenerationConfig,
    Content,
    Part,
    FunctionDeclaration,
    Tool,
)
import json
import os

logger = logging.getLogger(__name__)


class ChatAgent:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.chat_histories: Dict[str, List[Content]] = (
            {}
        )  # Store history as Gemini Content objects

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning(
                "GEMINI_API_KEY not found in environment. Gemini functionality will not work."
            )
            # Potentially raise an error or have a fallback if critical
            self.model = None
        else:
            genai.configure(api_key=api_key)
            # Using gemini-1.5-pro as it's good with function calling
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                # generation_config=GenerationConfig(temperature=0.7) # Optional: configure generation
            )

        self.gemini_tools = self._prepare_gemini_tools()

    def _prepare_gemini_tools(self) -> Optional[List[Tool]]:
        """
        Converts tools from ToolRegistry into the format expected by Gemini API.
        """
        if not self.tool_registry or not self.tool_registry.get_all_tools():
            return None

        function_declarations = []
        for tool_name, tool_callable in self.tool_registry.get_all_tools().items():
            # Attempt to parse parameters from the tool's docstring or other metadata
            # This is a simplified example. Real-world parsing might be more complex.
            # For now, we'll assume tools take kwargs.
            # A more robust solution would involve defining schemas for each tool's parameters.

            description = self.tool_registry.tool_descriptions.get(
                tool_name, "No description available."
            )

            # Simplified parameter schema - assuming all params are strings for now
            # In a real system, you'd define these based on your OpenAPI spec parameter types
            parameter_schema = {
                "type": "object",
                "properties": {
                    # Placeholder: You'd dynamically create this based on actual tool params
                    # e.g., "param_name": {"type": "string", "description": "description of param"}
                },
                # "required": ["param_name_if_required"] # If any params are required
            }

            # A more robust parameter extraction would be needed here.
            # For now, we are creating a generic placeholder.
            # Ideally, extract from endpoint_info['parameters'] and endpoint_info['request_body_schema']
            # during tool registration and store it.

            func_decl = FunctionDeclaration(
                name=tool_name,
                description=description,
                parameters=parameter_schema,  # This needs to be properly defined per tool
            )
            function_declarations.append(func_decl)

        if not function_declarations:
            return None
        return [Tool(function_declarations=function_declarations)]

    def _get_history(self, client_id: str) -> List[Content]:
        if client_id not in self.chat_histories:
            # Start with a system-level instruction if desired, or just empty.
            self.chat_histories[client_id] = []
        return self.chat_histories[client_id]

    def _add_to_history(self, client_id: str, role: str, parts: List[Part]):
        history = self._get_history(client_id)
        history.append(Content(role=role, parts=parts))
        # Optional: Trim history if it gets too long
        # MAX_HISTORY_LENGTH = 20
        # if len(history) > MAX_HISTORY_LENGTH:
        #     self.chat_histories[client_id] = history[-MAX_HISTORY_LENGTH:]

    async def process_chat(self, client_id: str, query: str) -> str:
        if not self.model:
            return "Error: Gemini AI model is not initialized. Please check API key."

        current_history = self._get_history(client_id)

        # Add user's query to history
        # Note: Gemini API expects a list of `Content` objects for history.
        # Each `Content` object has a role and parts.
        user_query_content = Content(role="user", parts=[Part(text=query)])

        # Prepare messages for Gemini: history + current query
        messages_for_gemini = current_history + [user_query_content]

        try:
            logger.info(
                f"Sending to Gemini for client '{client_id}': Query: '{query}' with {len(current_history)} history turns."
            )
            if self.gemini_tools:
                logger.info(
                    f"Providing {len(self.gemini_tools[0].function_declarations)} tools to Gemini."
                )

            # First API call to Gemini
            response = self.model.generate_content(
                messages_for_gemini,
                tools=self.gemini_tools if self.gemini_tools else None,
            )

            # Add user query to persistent history *after* it's been processed by Gemini,
            # so it's part of the turn.
            self._add_to_history(client_id, "user", [Part(text=query)])

            response_parts = response.candidates[0].content.parts

            final_text_response = ""

            for part in response_parts:
                if part.function_call:
                    function_call = part.function_call
                    tool_name = function_call.name
                    tool_args = dict(
                        function_call.args
                    )  # Convert from FunctionCall.args (Message) to dict

                    logger.info(
                        f"Gemini requested tool call: {tool_name} with args: {tool_args}"
                    )

                    self._add_to_history(
                        client_id, "model", [part]
                    )  # Add model's request for function call to history

                    tool_function = self.tool_registry.get_tool(tool_name)
                    if tool_function:
                        try:
                            # This assumes tools are synchronous. If async, need to await.
                            # The create_dynamic_tool_function returns a sync function.
                            tool_result = tool_function(**tool_args)

                            logger.info(
                                f"Tool '{tool_name}' executed. Result: {str(tool_result)[:200]}..."
                            )  # Log snippet of result

                            # Send tool response back to Gemini
                            function_response_part = Part(
                                function_response=genai.types.FunctionResponse(
                                    name=tool_name,
                                    response={
                                        "result": tool_result
                                    },  # Gemini expects a dict
                                )
                            )
                            self._add_to_history(
                                client_id, "function", [function_response_part]
                            )  # Add tool result to history

                            # Second API call to Gemini with the tool's response
                            messages_after_tool_call = self._get_history(
                                client_id
                            )  # Get updated history

                            logger.info(
                                f"Sending tool response for '{tool_name}' back to Gemini."
                            )
                            response_after_tool = self.model.generate_content(
                                messages_after_tool_call,
                                tools=(
                                    self.gemini_tools if self.gemini_tools else None
                                ),  # Still provide tools in case it wants another
                            )

                            # Extract final text from this response
                            for sub_part in response_after_tool.candidates[
                                0
                            ].content.parts:
                                if sub_part.text:
                                    final_text_response += sub_part.text

                            self._add_to_history(
                                client_id,
                                "model",
                                response_after_tool.candidates[0].content.parts,
                            )

                        except Exception as e:
                            logger.error(
                                f"Error executing tool {tool_name}: {e}", exc_info=True
                            )
                            error_response_part = Part(
                                function_response=genai.types.FunctionResponse(
                                    name=tool_name,
                                    response={
                                        "error": f"Error executing tool: {str(e)}"
                                    },
                                )
                            )
                            self._add_to_history(
                                client_id, "function", [error_response_part]
                            )

                            # Let Gemini know about the error
                            messages_after_tool_error = self._get_history(client_id)
                            response_after_tool_error = self.model.generate_content(
                                messages_after_tool_error, tools=self.gemini_tools
                            )
                            for sub_part in response_after_tool_error.candidates[
                                0
                            ].content.parts:
                                if sub_part.text:
                                    final_text_response += sub_part.text
                            self._add_to_history(
                                client_id,
                                "model",
                                response_after_tool_error.candidates[0].content.parts,
                            )
                            if not final_text_response:  # Ensure some response
                                final_text_response = f"An error occurred while trying to use the tool: {tool_name}."

                    else:
                        logger.warning(f"Tool '{tool_name}' not found in registry.")
                        # Inform Gemini the tool is not found
                        error_response_part = Part(
                            function_response=genai.types.FunctionResponse(
                                name=tool_name,
                                response={
                                    "error": f"Tool '{tool_name}' is not available."
                                },
                            )
                        )
                        self._add_to_history(
                            client_id, "function", [error_response_part]
                        )
                        messages_after_tool_notfound = self._get_history(client_id)
                        response_after_tool_notfound = self.model.generate_content(
                            messages_after_tool_notfound, tools=self.gemini_tools
                        )
                        for sub_part in response_after_tool_notfound.candidates[
                            0
                        ].content.parts:
                            if sub_part.text:
                                final_text_response += sub_part.text
                        self._add_to_history(
                            client_id,
                            "model",
                            response_after_tool_notfound.candidates[0].content.parts,
                        )
                        if not final_text_response:
                            final_text_response = f"I tried to use a tool called '{tool_name}', but I couldn't find it."

                elif part.text:
                    final_text_response += part.text

            if not final_text_response and not any(
                p.function_call for p in response_parts
            ):
                # This case might happen if the model's first response was empty or only non-text/non-function-call.
                # Or if a function call was made, but the subsequent response with results yielded no text.
                logger.warning(
                    f"Gemini response for client '{client_id}' resulted in no actionable text or function calls initially, or after a tool call. Response: {response}"
                )
                final_text_response = "I received a response, but I'm not sure how to proceed. Could you try rephrasing?"
                self._add_to_history(
                    client_id, "model", [Part(text=final_text_response)]
                )  # Add this fallback to history

            elif final_text_response and not any(
                p.function_call for p in response_parts
            ):  # If initial response was text, add it to history
                self._add_to_history(
                    client_id, "model", response.candidates[0].content.parts
                )

            # If final_text_response is still empty after potential tool calls, provide a generic message.
            if not final_text_response:
                final_text_response = "I've processed your request. If you were expecting a specific action, please let me know how I can assist further."
                # Avoid adding a duplicate "model" entry if one was already added from a tool's response.
                # This is more of a safeguard.
                if (
                    current_history[-1].role != "model"
                    or current_history[-1].parts[0].text != final_text_response
                ):
                    self._add_to_history(
                        client_id, "model", [Part(text=final_text_response)]
                    )

            return final_text_response.strip()

        except Exception as e:
            logger.error(
                f"Error in process_chat for client '{client_id}': {e}", exc_info=True
            )
            # Add user query to history even on error, then the error response
            self._add_to_history(
                client_id, "user", [Part(text=query)]
            )  # Ensure user query is in history
            error_msg = f"I encountered an unexpected error processing your request: {str(e)}. Please try again."
            self._add_to_history(client_id, "model", [Part(text=error_msg)])
            return error_msg


# Remove old helper methods that are no longer used:
# - _format_tools_for_gemini (replaced by _prepare_gemini_tools)
# - _extract_tool_calls (native function calling handles this)
