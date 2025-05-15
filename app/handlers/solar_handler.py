from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from app.handlers.base_handler import BaseQueryHandler
from app.core.history_manager import InMemoryChatHistory


class SolarQueryHandler(BaseQueryHandler):
    def _setup_agent(self):
        # Prompt specific to solar queries and Beckn retail flow
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a specialized assistant for solar panel installations and Beckn retail processes. "
                    "You can guide users through a multi-step process for solar item purchasing: select, confirm and then update.\n\n"
                    "BECKN RETAIL FLOW:\n"
                    "1. SEARCH: To search for solar items, use the 'beckn_search' tool, with the domain 'deg:retail' and the descriptor 'solar'. And reply with the available items in the response, including provider id and product id.\n"
                    "2. SELECT: After a successful search, if the user wishes to proceed, use the 'beckn_select' tool to select the item. And reply with the selected item and price.\n"
                    "Product id looks like this '1234' and provider id looks like this '5678'.\n"
                    # "3. CONFIRM: After a successful search, if the user wishes to proceed"
                    # f"3. UPDATE:Afer successful confirmation, you use the 'update_er_tool' tool to update the user's energy resource type to 'PROSUMER'. {self.client_id} is the 'client_id' (meter ID) from the user's query. Your response for this step should be the raw JSON output from the 'update_er_tool' tool.\n\n"
                    "GENERAL INSTRUCTIONS:\n"
                    "- When calling any tool, ensure you extract all necessary IDs and information from the ongoing conversation history or previous tool responses. "
                    "- If a user's query is a follow-up to a previous tool call, use the context from the chat history (including previous tool outputs you returned) to inform the next step.\n"
                    "- If the question is unrelated to solar energy or this retail flow, politely state your specialization.",
                ),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        if not self.llm:
            raise ValueError("LLM not initialized for SolarQueryHandler")
        if not self.tools:
            print(
                "Warning: SolarQueryHandler initialized with no tools, but it's expected to use them."
            )

        # This assumes self.llm is compatible with OpenAI tools agent (e.g., ChatOpenAI)
        try:
            agent = create_tool_calling_agent(self.llm, self.tools, prompt_template)
        except Exception as e:
            print(
                f"Could not create OpenAI tools agent for SolarHandler (LLM: {self.llm_config.model_name}): {e}. Ensure the model supports tool calling."
            )
            # Fallback like in GenericQueryHandler

            simple_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a specialized assistant for solar panel information.",
                    ),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{input}"),
                ]
            )
            self.agent_executor = simple_prompt | self.llm | StrOutputParser()
            print(
                "Warning: Agent creation for SolarQueryHandler failed. Tool usage might be affected."
            )
            return

        self.agent_executor = AgentExecutor(
            agent=agent, tools=self.tools, verbose=True, handle_parsing_errors=True
        )

    async def handle_query(self, query: str, chat_history: InMemoryChatHistory) -> str:
        if not self.agent_executor:
            return "I am currently unable to process your solar-related request due to an internal setup issue."

        history_messages = chat_history.messages if chat_history else []
        try:
            raw_response = await self.agent_executor.ainvoke(
                {"input": query, "chat_history": history_messages}
            )

            if isinstance(raw_response, dict):  # Output from AgentExecutor
                ai_response = raw_response.get(
                    "output",
                    f"Sorry, {self.__class__.__name__} could not extract output from response.",
                )
            elif isinstance(
                raw_response, str
            ):  # Output from LCEL chain with StrOutputParser
                ai_response = raw_response
            else:
                # Log this unexpected type for debugging
                print(
                    f"Unexpected response type from agent_executor in {self.__class__.__name__}: {type(raw_response)}"
                )
                ai_response = f"Sorry, {self.__class__.__name__} received an unexpected response format."
            return ai_response
        except Exception as e:
            print(f"Error during {self.__class__.__name__} agent execution: {e}")
            # import traceback # Optional: for more detailed error logging during development
            # traceback.print_exc()
            return f"An error occurred while processing your solar query in {self.__class__.__name__}. Please try again."
