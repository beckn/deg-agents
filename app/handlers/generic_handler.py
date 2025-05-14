# app/handlers/generic_handler.py
from langchain.agents import (
    AgentExecutor,
    create_openai_tools_agent,
)  # or other agent types
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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
                    "You are a helpful assistant. Answer the user's questions to the best of your ability. You have access to the following tools.",
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
            agent = create_openai_tools_agent(self.llm, self.tools, prompt_template)
        except Exception as e:
            # Fallback or different agent type if create_openai_tools_agent is not suitable
            # For instance, if the LLM doesn't support OpenAI function calling.
            print(
                f"Could not create OpenAI tools agent for GenericHandler (LLM: {self.llm_config.model_name}): {e}. Ensure the model supports tool calling."
            )
            # As a very basic fallback, you might create a simple chain without tools or a different agent type
            # For now, we'll let it proceed and it might fail at runtime if tools are called.
            # A more robust solution would be to select agent type based on LLM capabilities.
            # from langchain.chains.llm import LLMChain
            # self.agent_executor = LLMChain(llm=self.llm, prompt=ChatPromptTemplate.from_template("System: You are a helpful assistant.\nHuman: {input}\nAI:"))
            # return

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
            from langchain.chains.llm import LLMChain

            simple_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "You are a helpful assistant."),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{input}"),
                ]
            )
            self.agent_executor = LLMChain(llm=self.llm, prompt=simple_prompt)
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
            response = await self.agent_executor.ainvoke(
                {"input": query, "chat_history": history_messages}
            )
            return response.get("output", "Sorry, I could not generate a response.")
        except Exception as e:
            print(f"Error during GenericQueryHandler agent execution: {e}")
            # Fallback for models that don't handle chat_history well in invoke or if agent is simple LLMChain
            try:
                # If agent_executor is just an LLMChain, it might not expect 'chat_history'
                # This is a simplified error handling.
                if "chat_history" in str(e) and isinstance(
                    self.agent_executor, LLMChain
                ):
                    response = await self.agent_executor.ainvoke({"input": query})
                    return response.get(
                        "text", "Sorry, I could not generate a response."
                    )  # LLMChain output key is 'text'
                return f"An error occurred while processing your request: {e}"
            except Exception as final_e:
                print(f"Fallback error in GenericQueryHandler: {final_e}")
                return f"A critical error occurred: {final_e}"
