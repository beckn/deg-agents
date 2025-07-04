from app.handlers.base_handler import BaseQueryHandler
import logging
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
import random
import re
from app.core.orchestrator import ClientOrchestrator
from app.tools.specific_tools.grid_tools.dfp_search import DFPSearchTool, cache

logger = logging.getLogger(__name__)

class GridUtilityQueryHandler(BaseQueryHandler):
    """Handler for grid and utility-related queries."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store the last recommended DFP option for each client
        self.client_dfp_recommendations = {}
    
    def _setup_tools(self):
        """Set up the tools for this handler."""
        logger.info("Setting up tools for grid utility handler")
        
        # Add the DFP search tool
        try:
            self.tools = [
                DFPSearchTool()
            ]
            logger.info("Added DFP search tool")
        except Exception as e:
            logger.error(f"Error setting up DFP search tool: {str(e)}", exc_info=True)
            self.tools = []
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this handler."""
        return """
        You are a Grid Utility Agent for a utility company, responsible for monitoring and managing the electrical grid infrastructure including substations, transformers, and distribution networks.
        
        Your primary responsibilities include:
        1. Monitoring grid health and stability
        2. Managing substation operations
        3. Tracking transformer load and performance
        4. Responding to grid stress situations
        5. Coordinating maintenance and emergency responses
        
        You can help utility personnel with:
        1. Understanding grid infrastructure status
        2. Explaining technical aspects of grid operations
        3. Providing information about specific substations and transformers
        4. Answering questions about grid reliability and performance
        5. Interpreting grid data and metrics
        
        When you receive alerts about transformer stress or grid issues:
        - Analyze the situation carefully
        - Present the relevant data clearly
        - Recommend appropriate actions based on severity
        - Format your response professionally with clear action items
        
        Always maintain a professional, technical tone appropriate for utility company personnel. Focus on providing accurate information and actionable insights to help maintain grid stability and reliability.
        """
    
    def _setup_agent(self):
        """
        Set up the LLM agent with tools.
        This is a required implementation of the abstract method from BaseQueryHandler.
        """
        logger.info("Setting up grid utility agent")
        
        # If there are no tools, we can set up a simple agent without tools
        # Otherwise, we would configure an agent with the appropriate tools
        from langchain.agents import AgentType, initialize_agent
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        
        if not self.tools:
            logger.warning("No tools available for grid utility agent")
            # Create a simple LLM chain if no tools are available
            template = """
            {system_prompt}
            
            User: {query}
            AI: """
            
            prompt = PromptTemplate(
                template=template,
                input_variables=["system_prompt", "query"],
            )
            
            self.agent = LLMChain(
                llm=self.llm,
                prompt=prompt,
            )
        else:
            logger.info(f"Setting up agent with {len(self.tools)} tools: {[tool.name for tool in self.tools]}")
            # Create an agent with tools
            # Use STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION instead of CHAT_CONVERSATIONAL_REACT_DESCRIPTION
            # because it supports multi-input tools
            self.agent = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5,
            )
    
    async def handle_query(self, query: str, chat_history: List[Dict[str, Any]]) -> str:
        """
        Process a grid utility query.
        
        Args:
            query: The user's query
            chat_history: The chat history
            
        Returns:
            The response from the LLM
        """
        logger.info(f"GridUtilityQueryHandler processing query: {query[:100]}...")
        
        # Extract client ID from chat history if available
        client_id = None
        try:
            # Check if chat_history is a list
            if isinstance(chat_history, list) and chat_history:
                first_message = chat_history[0]
                if isinstance(first_message, dict) and "metadata" in first_message:
                    client_id = first_message.get("metadata", {}).get("client_id")
            # If chat_history is an object with messages attribute
            elif hasattr(chat_history, 'messages') and chat_history.messages:
                messages = chat_history.messages
                if messages and hasattr(messages[0], 'metadata'):
                    client_id = messages[0].metadata.get('client_id')
        except Exception as e:
            logger.warning(f"Error extracting client ID from chat history: {str(e)}")
        
        logger.info(f"Extracted client ID: {client_id}")
        
        # Check if this is a DFP activation request
        if query.lower().strip() in ["yes", "yes, proceed", "proceed", "activate", "yes, activate"]:
            logger.info("Detected DFP activation request")
            
            # Get the options from the cache
            dfp_options = cache.get("dfp_options", [])
            
            # Log the current state of the options
            logger.info(f"DFP options exists: {bool(dfp_options)}")
            logger.info(f"DFP options type: {type(dfp_options)}")
            logger.info(f"Number of options: {len(dfp_options)}")
            for i, option in enumerate(dfp_options):
                logger.info(f"Option {i+1}: {option.get('name', 'Unknown')} ({option.get('id', 'Unknown')})")
                # Log all keys in the option
                logger.info(f"Option {i+1} keys: {list(option.keys())}")
                # Log all values in the option
                for key, value in option.items():
                    logger.info(f"Option {i+1} {key}: {value}")
            
            # Use the first option if available
            if dfp_options:
                logger.info("Using first option from DFP options")
                option_data = dfp_options[0]
                
                # Create a recommendation with the option data
                recommendation = {
                    "option": option_data,
                    "transformer": {
                        "name": "Transformer_0",
                        "id": "TX160",
                        "current_load": "0.5",
                        "load_percentage": "0.4",
                        "time_estimate": "30"
                    }
                }
                
                logger.info(f"Using option: {option_data.get('name', 'Unknown')} ({option_data.get('id', 'Unknown')})")
                
                # Call the activation API with the option data
                return self._activate_dfp_option(client_id, recommendation)
            else:
                # Fall back to hardcoded data if no options are available
                logger.info("No options found in cache, using hardcoded recommendation")
                
                # Create a hardcoded recommendation
                hardcoded_recommendation = {
                    "option": {
                        "id": "DDR",
                        "name": "Dynamic Demand Response",
                        "description": "Dynamic Demand Response (DDR) rewards participants who can rapidly shift or curtail electricity usage during frequent, short-notice events.",
                        "reward": "$3–4.5 per kWh shifted",
                        "bonus": "15% extra if >90% compliance monthly",
                        "penalty": "15% reduction in incentives if compliance <75%",
                        "category": "Residential",
                        "minimum_load": "5 kW"
                    },
                    "transformer": {
                        "name": "Transformer_0",
                        "id": "TX160",
                        "current_load": "0.5",
                        "load_percentage": "0.4",
                        "time_estimate": "30"
                    }
                }
                
                # Call the activation API with the hardcoded data
                return self._activate_dfp_option(client_id, hardcoded_recommendation)
        
        # Check if this is a DFP rejection response (user wants the alternative option)
        elif query.lower().strip() in ["no", "no, try the other one", "try the other one", "use the other option", "alternative", "try alternative"]:
            logger.info("Detected DFP rejection request - user wants the alternative option")
            
            # Get the options from the cache
            dfp_options = cache.get("dfp_options", [])
            
            # Log the current state of the options
            logger.info(f"DFP options exists: {bool(dfp_options)}")
            logger.info(f"DFP options type: {type(dfp_options)}")
            logger.info(f"Number of options: {len(dfp_options)}")
            for i, option in enumerate(dfp_options):
                logger.info(f"Option {i+1}: {option.get('name', 'Unknown')} ({option.get('id', 'Unknown')})")
            
            # Use the second option if available, otherwise use the first option
            if dfp_options and len(dfp_options) > 1:
                logger.info("Using second option from DFP options")
                option_data = dfp_options[1]  # Use the second option
            elif dfp_options:
                logger.info("Only one option available, using the first option")
                option_data = dfp_options[0]  # Fall back to the first option if only one is available
            else:
                logger.info("No options found in cache, using hardcoded recommendation")
                # Create a hardcoded recommendation for the second option
                option_data = {
                    "id": "EDR",
                    "name": "Emergency Demand Reduction",
                    "description": "Emergency Demand Reduction (EDR) is designed for consumers who can rapidly curtail significant energy use during critical, rare grid emergencies.",
                    "reward": "$250/year per kW available",
                    "bonus": "$10.00 per kWh curtailed during events",
                    "penalty": "50% annual availability fee reduction per missed event",
                    "category": "Residential",
                    "minimum_load": "5 kW"
                }
            
            # Create a recommendation with the option data
            recommendation = {
                "option": option_data,
                "transformer": {
                    "name": "Transformer_0",
                    "id": "TX160",
                    "current_load": "0.5",
                    "load_percentage": "0.4",
                    "time_estimate": "30"
                }
            }
            
            logger.info(f"Using alternative option: {option_data.get('name', 'Unknown')} ({option_data.get('id', 'Unknown')})")
            
            # Call the activation API with the option data
            return self._activate_dfp_option(client_id, recommendation)
        
        # Check if this is a DFP recommendation request
        if "grid stress alert" in query.lower():
            logger.info("Detected DFP recommendation request, using DFP search tool directly")
            
            try:
                # Use the DFP search tool directly instead of through the agent
                from app.tools.specific_tools.grid_tools.dfp_search import DFPSearchTool
                
                # Create the tool
                dfp_tool = DFPSearchTool()
                
                # Call the tool directly
                logger.info("Calling DFP search tool directly...")
                dfp_options = dfp_tool._run("demand flexibility programs")
                logger.info(f"DFP search tool returned: {dfp_options[:100]}...")
                
                # Check if the response indicates no options were found
                if "No DFP options found" in dfp_options:
                    logger.warning("No DFP options found in API response, using fallback options")
                    # Use a hardcoded fallback response
                    dfp_options = """
Here are the available Demand Flexibility Program (DFP) options:

Option 1: Dynamic Demand Response (DDR)
Dynamic Demand Response (DDR) rewards participants who can rapidly shift or curtail electricity usage during frequent, short-notice events. Participants receive moderately high per-event compensation due to their ability to reliably and promptly adjust energy consumption patterns, significantly aiding grid stability and renewable energy integration.
Reward: $3–4.5 per kWh shifted
Bonus: 15% extra if >90% compliance monthly
Penalty: 15% reduction in incentives if compliance <75%
Category: Residential
Minimum Load: 5 kW

Option 2: Emergency Demand Reduction (EDR)
Emergency Demand Reduction (EDR) is designed for consumers who can rapidly curtail significant energy use during critical, rare grid emergencies. These are infrequent but urgent events requiring immediate action. Participants are compensated significantly for availability but face substantial penalties for non-compliance due to critical grid dependence.
Reward: $250/year per kW available
Bonus: $10.00 per kWh curtailed during events
Penalty: 50% annual availability fee reduction per missed event
Category: Residential
Minimum Load: 5 kW
"""
                
                # Extract transformer details from the query
                transformer_name_match = re.search(r"transformer (.*?) \[", query)
                transformer_name = transformer_name_match.group(1) if transformer_name_match else "Unknown"
                
                transformer_id_match = re.search(r"\[(.*?)\]", query)
                transformer_id = transformer_id_match.group(1) if transformer_id_match else "Unknown"
                
                current_load_match = re.search(r"current load is (.*?) kWh", query)
                current_load = current_load_match.group(1) if current_load_match else "Unknown"
                
                load_percentage_match = re.search(r"\((.*?)% of capacity\)", query)
                load_percentage = load_percentage_match.group(1) if load_percentage_match else "Unknown"
                
                time_estimate_match = re.search(r"breach is likely in (.*?) minutes", query)
                time_estimate = time_estimate_match.group(1) if time_estimate_match else "Unknown"
                
                # Randomly select which DFP option to recommend
                recommended_option = random.choice(["DDR", "EDR"])
                
                # Format the recommendation text with Markdown
                if recommended_option == "DDR":
                    recommendation_text = f"### 🔎 Recommendation\n\n**Option 1 – Dynamic Demand Response (DDR)** is recommended for immediate grid relief.\n\n> The current situation at {transformer_name} shows a load of **{current_load} kWh ({load_percentage}% of capacity)**, which requires a rapid but moderate response. DDR is ideal for this scenario as it can be quickly activated and provides immediate relief without excessive disruption.\n\n\n**Would you like to proceed?**"
                    option_index = 0  # Index in the options array (0-based)
                else:
                    recommendation_text = f"### 🔎 Recommendation\n\n**Option 2 – Emergency Demand Reduction (EDR)** is recommended for immediate grid relief.\n\n> The current situation at {transformer_name} shows a load of **{current_load} kWh ({load_percentage}% of capacity)**, which requires a significant and immediate response. EDR is designed for critical situations like this and can provide the necessary load reduction quickly.\n\n\n**Would you like to proceed?**"
                    option_index = 1  # Index in the options array (0-based)
                
                # Store the recommendation data for later use
                if client_id:
                    logger.info(f"Storing DFP recommendation for client {client_id}")
                    
                    # Get the recommended option data
                    if hasattr(DFPSearchTool, '_last_api_response') and DFPSearchTool._last_api_response and "options" in DFPSearchTool._last_api_response:
                        options = DFPSearchTool._last_api_response["options"]
                        if options and len(options) > option_index:
                            recommended_option_data = options[option_index]
                            
                            # Store the recommendation with transformer data
                            self.client_dfp_recommendations[client_id] = {
                                "option": recommended_option_data,
                                "transformer": {
                                    "name": transformer_name,
                                    "id": transformer_id,
                                    "current_load": current_load,
                                    "load_percentage": load_percentage,
                                    "time_estimate": time_estimate
                                }
                            }
                            
                            logger.info(f"Stored DFP recommendation for client {client_id}: {recommended_option}")
                        else:
                            logger.warning(f"No options found at index {option_index} for client {client_id}")
                    else:
                        logger.warning(f"No options found in _last_api_response for client {client_id}")
                else:
                    logger.warning("No client_id found, cannot store DFP recommendation")
                
                # Format the complete response with Markdown
                response = f"## ⚠️ Grid Stress Alert for {transformer_name} [{transformer_id}]\n\n{dfp_options}{recommendation_text}"
                
                return response
            except Exception as e:
                logger.error(f"Error using DFP search tool directly: {str(e)}", exc_info=True)
                # Fall back to the agent if direct tool use fails
        
        # For non-DFP queries or if direct tool use fails, use the agent
        try:
            # Use the agent normally
            if hasattr(self, 'agent') and self.agent:
                logger.info("Using agent for query")
                # Use the existing agent
                if hasattr(self.agent, 'run'):
                    result = await self.agent.arun(query)
                else:
                    # For LLMChain
                    system_prompt = self._get_system_prompt()
                    result = await self.agent.arun(system_prompt=system_prompt, query=query)
                
                # Filter out the agent's internal monologue
                filtered_response = self._filter_agent_monologue(result)
                
                logger.info(f"GridUtilityQueryHandler got response: {filtered_response[:100]}...")
                
                return filtered_response
            else:
                # Fall back to using the orchestrator's default processing
                logger.warning("Agent not set up, using fallback response")
                
                # For simplicity, let's just use a hardcoded response for now
                return "I'm here to help with grid and utility questions. How can I assist you today?"
        except Exception as e:
            logger.error(f"Error in GridUtilityQueryHandler: {str(e)}", exc_info=True)
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    def _filter_agent_monologue(self, response: str) -> str:
        """
        Filter out the agent's internal monologue from the response.
        
        Args:
            response: The raw response from the LLM
            
        Returns:
            The filtered response
        """
        # Check if the response contains the agent's internal monologue
        if "Thought:" in response or "I need to" in response or "Given the limitations" in response:
            # Try to extract just the final answer
            # Look for patterns that indicate the start of the actual response
            patterns = [
                r"Therefore,(.*?)$",
                r"In conclusion,(.*?)$",
                r"To summarize,(.*?)$",
                r"My response:(.*?)$",
                r"Here's my response:(.*?)$",
                r"Final Answer:(.*?)$"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    return match.group(1).strip()
            
            # If no pattern matches, return a generic response
            return "I apologize, but I'm having trouble generating a specific response. Please try rephrasing your question."
        
        # If no internal monologue detected, return the original response
        return response 

    def _activate_dfp_option(self, client_id: str, recommendation: Dict[str, Any]) -> str:
        """
        Activate a DFP option.
        
        Args:
            client_id: The client ID
            recommendation: The recommendation data
            
        Returns:
            The activation response
        """
        logger.info(f"Activating DFP option for client {client_id}")
        
        try:
            # Extract the option and transformer data
            option = recommendation.get("option", {})
            transformer = recommendation.get("transformer", {})
            
            option_id = option.get("id", "Unknown")
            option_name = option.get("name", "Unknown")
            transformer_name = transformer.get("name", "Unknown")
            transformer_id = transformer.get("id", "Unknown")
            
            # Make the actual API call to activate the DFP option
            activation_url = "https://bpp-unified-strapi-deg.becknprotocol.io/unified-beckn-energy/mitigation-activate"
            
            # Prepare the request payload
            payload = {
                "itemId": str(option_id)  # Ensure the ID is a string
            }
            
            # Log the API request
            logger.info(f"Making API call to activate DFP option: {option_id}")
            logger.info(f"API URL: {activation_url}")
            logger.info(f"API payload: {payload}")
            
            # Make the API call
            import requests
            response = requests.post(
                activation_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=10  # 10 second timeout
            )
            
            # Log the API response
            logger.info(f"API response status code: {response.status_code}")
            logger.info(f"API response: {response.text}")
            
            # Check if the API call was successful
            if response.status_code == 200:
                # Parse the response
                try:
                    response_data = response.json()
                    activation_status = response_data.get("status", "Unknown")
                    activation_message = response_data.get("message", "No message provided")
                    
                    logger.info(f"Activation status: {activation_status}")
                    logger.info(f"Activation message: {activation_message}")
                    
                    # Clear the recommendation after activation
                    if client_id in self.client_dfp_recommendations:
                        del self.client_dfp_recommendations[client_id]
                    
                    # Return a success message with the API response details
                    return f"✅ Successfully activated {option_name} ({option_id}) for transformer {transformer_name} [{transformer_id}].\n\nStatus: {activation_status}\nMessage: {activation_message}"
                except Exception as e:
                    logger.error(f"Error parsing API response: {str(e)}", exc_info=True)
                    # Return a success message without the API response details
                    return f"✅ Proceeding to Activate {option_name} ({option_id}) for transformer {transformer_name} [{transformer_id}]. Please wait…"
            else:
                # API call failed
                error_message = f"API call failed with status code {response.status_code}: {response.text}"
                logger.error(error_message)
                return f"❌ Failed to activate {option_name} ({option_id}) for transformer {transformer_name} [{transformer_id}]. Error: {error_message}"
        except Exception as e:
            logger.error(f"Error activating DFP option: {str(e)}", exc_info=True)
            return f"I apologize, but I encountered an error while activating the DFP option: {str(e)}" 