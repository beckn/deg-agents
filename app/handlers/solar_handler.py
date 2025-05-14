from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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
            from langchain.chains.llm import LLMChain

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
            self.agent_executor = LLMChain(llm=self.llm, prompt=simple_prompt)
            print(
                f"Warning: Agent creation for SolarQueryHandler failed. Tool usage might be affected."
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
            response = await self.agent_executor.ainvoke(
                {"input": query, "chat_history": history_messages}
            )
            return response.get(
                "output", "Sorry, I could not provide a solar-specific response."
            )
        except Exception as e:
            print(f"Error during SolarQueryHandler agent execution: {e}")
            try:
                if "chat_history" in str(e) and isinstance(
                    self.agent_executor, LLMChain
                ):
                    response = await self.agent_executor.ainvoke({"input": query})
                    return response.get(
                        "text", "Sorry, I could not generate a response."
                    )
                return f"An error occurred while processing your solar query: {e}"
            except Exception as final_e:
                print(f"Fallback error in SolarQueryHandler: {final_e}")
                return f"A critical error occurred in solar processing: {final_e}"
