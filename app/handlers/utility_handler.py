from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from app.handlers.base_handler import BaseQueryHandler
from app.core.history_manager import InMemoryChatHistory


class UtilityQueryHandler(BaseQueryHandler):
    def _setup_agent(self):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a grid manager. "
                    "When you receive a query that says that a transormer is going to reach its allowed load, you need to call the on_status tool to employ the load shedding plan.",
                ),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        if not self.llm:
            raise ValueError("LLM not initialized for UtilityQueryHandler")
        if not self.tools:
            print("Warning: UtilityQueryHandler initialized with no tools.")

        try:
            agent = create_tool_calling_agent(self.llm, self.tools, prompt_template)
        except Exception as e:
            print(
                f"Could not create tools agent for UtilityHandler (LLM: {self.llm_config.model_name}): {e}. Ensure the model supports tool calling."
            )

            simple_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "You are a helpful assistant."),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{input}"),
                ]
            )
            self.agent_executor = simple_prompt | self.llm | StrOutputParser()
            print(
                "Warning: Agent creation for UtilityQueryHandler failed. Tool usage might be affected."
            )
            return

        self.agent_executor = AgentExecutor(
            agent=agent, tools=self.tools, verbose=False, handle_parsing_errors=True
        )

    async def handle_query(self, query: str, chat_history: InMemoryChatHistory) -> str:
        if not self.agent_executor:
            return "I am currently unable to process your utility request due to an internal setup issue."

        history_messages = chat_history.messages if chat_history else []
        try:
            raw_response = await self.agent_executor.ainvoke(
                {"input": query, "chat_history": history_messages}
            )
            if isinstance(raw_response, dict):
                return raw_response["output"]
            else:
                return str(raw_response)
        except Exception as e:
            print(f"Error during query handling by UtilityQueryHandler: {e}")
            return f"I encountered an error trying to process your request: {e}"
