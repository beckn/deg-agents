# app/handlers/generic_handler.py
from langchain.agents import (
    AgentExecutor,
    create_tool_calling_agent,
)  # or other agent types
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from app.handlers.base_handler import BaseQueryHandler
from app.core.history_manager import InMemoryChatHistory  # or BaseChatMessageHistory


class GenericQueryHandler(BaseQueryHandler):
    def _setup_agent(self):
        # Example prompt for a generic conversational agent
        # You can load this from a file or define it more elaborately
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a residential energy assistant helping consumers actively manage their energy usage, support grid reliability, and adopt solar energy solutions.\n\n"
                    "Your core capabilities:\n"
                    "1. **Demand Flexibility Participation**\n"
                    "   - Detect local grid stress or utility signals.\n"
                    "   - Notify users with clear details and incentive offers.\n"
                    "   - Suggest energy reduction plans by turning off specific DERs (e.g., HVAC, EV charging, dishwasher).\n"
                    "   - Request user consent for remote control actions.\n"
                    "   - Log participation and report outcomes.\n\n"
                    "2. **Buy Solar Panels and Battery Systems**\n"
                    "   - Proactively offer to help users explore rooftop solar and battery storage.\n"
                    "   - Based on user interest or prompt (\"I want solar\"), guide them through:\n"
                    "     - Site survey scheduling\n"
                    "     - System design options\n"
                    "     - Subsidy discovery and application (e.g., federal tax credits, state rebates)\n"
                    "     - Installer coordination\n"
                    "   - Confirm post-installation tasks: DER registration, net metering, flexibility opt-in.\n\n"
                    "3. **User Experience Management**\n"
                    "   - Always ask for permission before controlling devices.\n"
                    "   - Support voice/text chat.\n"
                    "   - Track energy events, report earnings, and suggest monthly targets.\n"
                    "   - Maintain friendly, helpful, and concise tone.\n\n"
                    "Context: User resides in a smart home in San Francisco, with DERs and interest in clean energy participation.\n"
                    "Goal: Maximize user comfort, savings, and contribution to grid resilience.",
                ),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        if not self.llm:
            raise ValueError("LLM not initialized for GenericQueryHandler")
        if not self.tools:
            print("Warning: GenericQueryHandler initialized with no tools.")

        # Create an agent. For OpenAI models, create_openai_tools_agent is common.
        # Adjust if using other LLM providers or agent types (e.g., ReAct, StructuredChatAgent)
        # This assumes self.llm is compatible (e.g., ChatOpenAI)
        try:
            agent = create_tool_calling_agent(self.llm, self.tools, prompt_template)
        except Exception as e:
            # Fallback or different agent type if create_openai_tools_agent is not suitable
            # For instance, if the LLM doesn't support OpenAI function calling.
            print(
                f"Could not create OpenAI tools agent for GenericHandler (LLM: {self.llm_config.model_name}): {e}. Ensure the model supports tool calling."
            )
            # As a very basic fallback, you might create a simple chain without tools or a different agent type
            # For now, we'll let it proceed and it might fail at runtime if tools are called.
            # A more robust solution would be to select agent type based on LLM capabilities.

            # If using a ReAct style agent (more general but older)
            # from langchain.agents import initialize_agent, AgentType
            # self.agent_executor = initialize_agent(
            #     self.tools,
            #     self.llm,
            #     agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, # Or another suitable agent type
            #     verbose=True,
            #     handle_parsing_errors=True
            # )
            # For simplicity in this example, we'll assume create_openai_tools_agent works or tools are optional
            # If tools are essential, this should raise an error or implement a proper fallback.
            # For now, if it fails, self.agent_executor might remain None or be set to a non-tool-using chain.
            print(
                f"Warning: Agent creation for GenericQueryHandler failed. Tool usage might be affected."
            )
            # Create a dummy agent executor if the primary one fails to allow the system to run
            # This is a simplified approach for now.
            simple_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "You are a helpful assistant."),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{input}"),
                ]
            )
            self.agent_executor = simple_prompt | self.llm | StrOutputParser()
            return

        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,  # For debugging
            handle_parsing_errors=True,  # Useful for more complex agents
        )

    async def handle_query(self, query: str, chat_history: InMemoryChatHistory) -> str:
        if not self.agent_executor:
            # This case implies _setup_agent failed to create a working executor
            return "I am currently unable to process your request due to an internal setup issue."

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
            return f"An error occurred while processing your request in {self.__class__.__name__}. Please try again."
