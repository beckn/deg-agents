import logging
from typing import Dict, Any, Optional, List
import asyncio
from app.config.settings import settings, AppConfig

logger = logging.getLogger(__name__)

class LLMManager:
    _instance = None
    _initialized_models = {}
    _initialization_lock = asyncio.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = LLMManager()
        return cls._instance

    async def get_llm(self, llm_config_name: str):
        """
        Get or initialize an LLM instance based on the config name.
        
        Args:
            llm_config_name: The name of the LLM configuration in the app config
            
        Returns:
            The initialized LLM instance
        """
        if llm_config_name in self._initialized_models:
            logger.debug(f"Using cached LLM instance for {llm_config_name}")
            return self._initialized_models[llm_config_name]
        
        # Use a lock to prevent multiple initializations of the same model
        async with self._initialization_lock:
            # Check again in case another thread initialized it while we were waiting
            if llm_config_name in self._initialized_models:
                return self._initialized_models[llm_config_name]
            
            logger.info(f"Initializing new LLM instance for {llm_config_name}")
            
            # Get the app config
            app_config = settings
            
            # Get the LLM config
            llm_config = getattr(app_config.llms, llm_config_name, None)
            if not llm_config:
                raise ValueError(f"LLM config {llm_config_name} not found")
            
            # Initialize the LLM based on the provider
            provider = llm_config.provider.lower()
            
            if provider == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                
                model = ChatGoogleGenerativeAI(
                    model=llm_config.model_name,
                    temperature=llm_config.temperature,
                    convert_system_message_to_human=True,
                )
            elif provider == "openai":
                from langchain_openai import ChatOpenAI
                
                model = ChatOpenAI(
                    model=llm_config.model_name,
                    temperature=llm_config.temperature,
                )
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                
                model = ChatAnthropic(
                    model=llm_config.model_name,
                    temperature=llm_config.temperature,
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
            
            # Cache the initialized model
            self._initialized_models[llm_config_name] = model
            
            return model

    async def generate_response(self, query: str, chat_history: List[Dict[str, Any]], 
                               system_prompt: str, llm_config: Any) -> str:
        """
        Generate a response using the specified LLM.
        
        Args:
            query: The user's query
            chat_history: The chat history
            system_prompt: The system prompt
            llm_config: The LLM configuration
            
        Returns:
            The generated response
        """
        try:
            # Get the LLM instance
            llm = await self.get_llm(llm_config.llm_config_name)
            
            # Format the messages for the LLM
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
            
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # Add chat history
            for message in chat_history:
                if message["role"] == "user":
                    messages.append(HumanMessage(content=message["content"]))
                elif message["role"] == "assistant":
                    messages.append(AIMessage(content=message["content"]))
            
            # Add the current query
            messages.append(HumanMessage(content=query))
            
            # Generate the response
            response = await llm.ainvoke(messages)
            
            # Extract the content from the response
            return response.content
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise 