from app.handlers.base_handler import BaseQueryHandler
import logging
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

class GridUtilityQueryHandler(BaseQueryHandler):
    """Handler for grid and utility-related queries."""
    
    def _setup_tools(self):
        """Set up the tools for this handler."""
        # For now, we'll use the general knowledge tool
        # Later, we can add grid-specific tools
        self.tools = []
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this handler."""
        return """
        You are a helpful assistant specializing in electric grid and utility services.
        
        You can help users with:
        1. Understanding their electricity bill
        2. Explaining grid infrastructure and operations
        3. Providing information about utility programs and services
        4. Answering questions about power outages and reliability
        5. Explaining electricity rates and pricing structures
        
        Always be informative, accurate, and helpful. If you don't know something, 
        acknowledge that and suggest where the user might find more information.
        """
    
    def _setup_agent(self):
        """
        Set up the LLM agent with tools.
        This is a required implementation of the abstract method from BaseQueryHandler.
        """
        # If there are no tools, we can set up a simple agent without tools
        # Otherwise, we would configure an agent with the appropriate tools
        from langchain.agents import AgentType, initialize_agent
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        
        if not self.tools:
            # Create a simple LLM chain if no tools are available
            template = """
            {system_prompt}
            
            User: {query}
            AI Assistant:
            """
            prompt = PromptTemplate(
                input_variables=["system_prompt", "query"],
                template=template
            )
            self.agent = LLMChain(llm=self.llm, prompt=prompt)
        else:
            # Initialize an agent with tools if available
            self.agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True
            )
    
    async def handle_query(self, query: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        """
        Handle a query and return a response.
        This is a required implementation of the abstract method from BaseQueryHandler.
        
        Args:
            query: The user's query
            chat_history: Optional chat history
            
        Returns:
            The response to the query
        """
        try:
            system_prompt = self._get_system_prompt()
            
            if not self.tools:
                # If using a simple LLM chain
                response = await self.agent.arun(system_prompt=system_prompt, query=query)
            else:
                # If using an agent with tools
                # We might need to format the input differently based on the agent type
                response = await self.agent.arun(
                    f"System: {system_prompt}\nUser query: {query}"
                )
                
            return response
        except Exception as e:
            logger.error(f"Error handling query in GridUtilityQueryHandler: {e}")
            return f"I'm sorry, I encountered an error while processing your request: {str(e)}" 