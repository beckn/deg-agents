from langchain.agents import (
    AgentExecutor,
    create_tool_calling_agent,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from app.handlers.base_handler import BaseQueryHandler
from app.core.history_manager import InMemoryChatHistory


class GenericQueryHandler(BaseQueryHandler):
    def _setup_agent(self):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant with specialized knowledge in solar panel installations and DFP (Demand Flexibility Program) queries. You have access to tools to help with these topics.",
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

        try:
            agent = create_tool_calling_agent(self.llm, self.tools, prompt_template)
        except Exception as e:
            print(
                f"Could not create tools agent for GenericHandler (LLM: {self.llm_config.model_name}): {e}. Ensure the model supports tool calling."
            )
            print(
                f"Warning: Agent creation for GenericQueryHandler failed. Tool usage might be affected."
            )
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
            verbose=True,
            handle_parsing_errors=True,
        )

    async def handle_query(self, query: str, chat_history: InMemoryChatHistory) -> str:
        if not self.agent_executor:
            return "I am currently unable to process your request due to an internal setup issue."

        history_messages = chat_history.messages if chat_history else []
        try:
            raw_response = await self.agent_executor.ainvoke(
                {"input": query, "chat_history": history_messages}
            )

            if isinstance(raw_response, dict):
                ai_response = raw_response.get(
                    "output",
                    f"Sorry, {self.__class__.__name__} could not extract output from response.",
                )
            elif isinstance(raw_response, str):
                ai_response = raw_response
            else:
                print(
                    f"Unexpected response type from agent_executor in {self.__class__.__name__}: {type(raw_response)}"
                )
                ai_response = f"Sorry, {self.__class__.__name__} received an unexpected response format."
            return ai_response
        except Exception as e:
            print(f"Error during {self.__class__.__name__} agent execution: {e}")
            return f"An error occurred while processing your request in {self.__class__.__name__}. Please try again."
