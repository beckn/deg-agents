from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from app.handlers.base_handler import BaseQueryHandler
from app.core.history_manager import InMemoryChatHistory  # or BaseChatMessageHistory


class SolarQueryHandler(BaseQueryHandler):
    def _setup_agent(self):
        # Prompt specific to solar queries
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a specialized assistant for solar panel installations and information. "
                    "Focus on answering questions related to solar energy, panel calculations, "
                    "installation processes, and benefits. Use your tools when appropriate. "
                    "If the question is unrelated to solar energy, politely state your specialization.",
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
            agent = create_openai_tools_agent(self.llm, self.tools, prompt_template)
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
