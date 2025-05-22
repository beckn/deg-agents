from fastapi import APIRouter, BackgroundTasks, HTTPException, Body
from typing import Dict, Any, List, Set, Optional
import logging
import random
import asyncio
import requests
import json
from app.core.websocket_manager import connection_manager
from app.core.orchestrator import ClientOrchestrator
import uuid
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["grid_alerts"])

class SimpleGridAlertRequest(BaseModel):
    # No required fields
    pass

@router.post("/grid-alerts/consumer")
async def simple_grid_alert(request: Dict[str, Any] = Body(...)):
    """
    Endpoint to receive Beckn protocol grid alerts and send to connected clients.
    """
    logger.info(f"Received grid alert request payload")
    
    # Track successful sends
    successful_sends = 0
    
    # Log the request payload
    logger.info(f"Request payload: {json.dumps(request, indent=2)}")
    
    try:
        # Extract order_id from the Beckn protocol request
        order_id = None
        
        # Navigate through the nested structure to find the order ID
        if "responses" in request and len(request["responses"]) > 0:
            response = request["responses"][0]
            if "message" in response and "order" in response["message"]:
                order = response["message"]["order"]
                order_id = order.get("id")
        
        if not order_id:
            logger.error("Could not extract order_id from request")
            return {"status": "error", "message": "Could not extract order_id from request"}
        
        logger.info(f"Extracted order_id: {order_id}")
        
        # Fetch meter IDs associated with the order_id
        meter_ids = await fetch_meter_ids_by_subscription(order_id)
        
        if not meter_ids:
            logger.warning(f"No meters found for order_id: {order_id}")
            return {"status": "warning", "message": f"No meters found for order_id: {order_id}"}
        
        logger.info(f"Found meter IDs: {meter_ids}")
        
        # Create a grid alert message
        alert_message = {
            "type": "grid_alert",
            "status": "success",
            "message": "⚠️ Attention! We have detected a grid overload in your area. To help stabilize the grid, we are activating our Demand Flexibility Program.\n\nWould you like to participate?\n✅ Incentives: Earn $3–4.5 per kWh of reduced consumption\n✅ Incentives: 15% bonus if you maintain >90% participation this month.",
            "order_id": order_id
        }
        
        # Send alert to users with matching meter IDs
        for meter_id in meter_ids:
            # Get connection ID for this meter ID
            connection_id = connection_manager.get_connection_by_meter_id(str(meter_id))
            
            if connection_id:
                # Send the alert
                success = await connection_manager.send_message(connection_id, alert_message)
                if success:
                    successful_sends += 1
                    logger.info(f"Alert sent successfully to meter ID: {meter_id}, connection ID: {connection_id}")
                else:
                    logger.warning(f"Failed to send alert to meter ID: {meter_id}, connection ID: {connection_id}")
            else:
                logger.warning(f"No active connection found for meter ID: {meter_id}")
        
        return {
            "status": "success", 
            "message": f"Alert sent to {successful_sends} clients with matching meter IDs",
            "order_id": order_id,
            "meters_count": len(meter_ids),
            "successful_sends": successful_sends
        }
        
    except Exception as e:
        logger.error(f"Error processing grid alert: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Error processing grid alert: {str(e)}"}

async def fetch_meter_ids_by_subscription(subscription_id: str) -> List[int]:
    """
    Fetch meter IDs associated with a subscription ID.
    """
    # API URL for fetching meters by subscription ID
    api_url = f"https://playground.becknprotocol.io/meter-data-simulator/meters/subscription/{subscription_id}"
    
    try:
        # Make the API request
        response = requests.get(api_url, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the response
            data = response.json()
            
            # Extract meter IDs from the response
            meter_ids = []
            if "data" in data and isinstance(data["data"], list):
                for meter in data["data"]:
                    if "id" in meter:
                        meter_ids.append(meter["id"])
            
            logger.info(f"Found {len(meter_ids)} meters for subscription ID {subscription_id}: {meter_ids}")
            return meter_ids
        else:
            logger.error(f"API request failed with status code {response.status_code}: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching meters by subscription: {str(e)}")
        return []

@router.post("/grid-alerts/transformer-stress")
async def transformer_stress_alert(data: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Endpoint to receive transformer stress alerts and broadcast to connected clients.
    """
    logger.info(f"Received transformer stress alert: {data}")
    
    # Extract transformer details
    transformer = data.get("transformer", {})
    transformer_id = transformer.get("id")
    transformer_name = transformer.get("name", "Unknown")
    city = transformer.get("city", "Unknown")
    state = transformer.get("state", "Unknown")
    max_capacity_kw = transformer.get("max_capacity_KW", 0)
    current_load_kwh = data.get("totalBaseKWh", 0)
    
    # Extract substation details
    substation = transformer.get("substation", {})
    substation_name = substation.get("name", "Unknown")
    
    # Calculate load percentage
    load_percentage = (current_load_kwh / max_capacity_kw) * 100 if max_capacity_kw else 0
    
    # Format the transformer ID for display (e.g., TX005)
    display_id = f"TX{transformer_id:03d}" if transformer_id else "Unknown"
    
    # Generate a random time estimate between 25-35 minutes
    time_estimate = random.randint(25, 35)
    
    # Format the alert message with more details
    alert_message = (
        f"⚠️ Grid Stress Detected at {transformer_name} [{display_id}] – "
        f"Capacity Breach Likely in {time_estimate} Minutes.\n\n"
        f"Location: {city}, {state}\n"
        f"Substation: {substation_name}\n"
        f"Current Load: {current_load_kwh:.2f} kWh ({load_percentage:.1f}% of capacity)\n"
        f"Maximum Capacity: {max_capacity_kw} kW"
    )
    
    # Prepare transformer data for the client
    transformer_data = {
        "transformer_id": transformer_id,
        "display_id": display_id,
        "name": transformer_name,
        "city": city,
        "state": state,
        "max_capacity_kw": max_capacity_kw,
        "current_load_kwh": current_load_kwh,
        "load_percentage": load_percentage,
        "time_estimate": time_estimate,
        "substation_name": substation_name
    }
    
    # Broadcast the alert in the background to avoid blocking the response
    background_tasks.add_task(process_grid_alert, alert_message, transformer_data)
    
    return {"status": "success", "message": "Alert broadcasted to connected clients"}


async def process_grid_alert(alert_message: str, transformer_data: Dict[str, Any]):
    """
    Process a grid alert using the agent.
    """
    try:
        # Step 1: Broadcast the alert
        logger.info("Broadcasting grid alert...")
        client_connections = await broadcast_grid_alert(alert_message, transformer_data)
        
        if not client_connections:
            logger.warning("No client connections found, skipping DFP recommendations")
            return
        
        logger.info(f"Found {len(client_connections)} client connections")
        
        # Step 2: For each client, get agent recommendations
        for connection_id in client_connections:
            try:
                client_id = connection_manager.get_client(connection_id)
                if not client_id:
                    # Generate a default client ID if none exists
                    client_id = f"grid_client_{str(uuid.uuid4())[:8]}"
                    logger.info(f"No client ID found for connection {connection_id}, generating default: {client_id}")
                    connection_manager.set_client(connection_id, client_id)
                
                logger.info(f"Processing for client {client_id}, connection {connection_id}")
                
                # Add alert to chat history as a "system" user message instead of using add_system_message
                orchestrator = ClientOrchestrator.get_instance(client_id)
                # Use add_user_message with a special prefix instead of add_system_message
                orchestrator.history_manager.add_user_message(
                    client_id, 
                    f"[SYSTEM ALERT] {alert_message}"
                )
                
                # Wait a moment before sending agent request (for better UX)
                logger.info("Waiting before sending agent request...")
                await asyncio.sleep(2)
                
                # Get DFP recommendations from agent
                logger.info("Getting DFP recommendations from agent...")
                agent_response = await get_agent_dfp_recommendation(client_id, transformer_data)
                
                # Store transformer data for this client
                logger.info("Storing transformer data for client...")
                from app.routers.grid_utility_ws import transformer_data_store
                transformer_data_store[client_id] = transformer_data
                
                # Before sending the agent's response, check the client type
                logger.info("Checking client type before sending agent response...")
                client_type = connection_manager.get_client_type(connection_id)

                logger.info(f"Client type for connection {connection_id}: {client_type}")

                # Only send the alert to utility dashboard clients
                if client_type == "utility_dashboard":
                    logger.info("Sending agent response to utility dashboard client...")
                    await connection_manager.send_message(
                        connection_id,
                        {
                            "type": "dfp_options_and_recommendation",
                            "status": "success",
                            "message": agent_response,
                            "transformer_data": transformer_data
                        }
                    )
                else:
                    logger.info(f"Skipping alert for non-utility client (type: {client_type})")
            except Exception as e:
                logger.error(f"Error processing client {connection_id}: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Error in process_grid_alert: {str(e)}", exc_info=True)


async def broadcast_grid_alert(alert_message: str, transformer_data: Dict[str, Any]) -> Set[str]:
    """
    Broadcasts a grid alert to all connected WebSocket clients.
    
    Returns:
        Set of connection IDs that received the alert
    """
    # Get all client connections
    client_connections = connection_manager.get_all_connections()
    
    if not client_connections:
        logger.warning("No connected clients to broadcast alert to")
        return set()
    
    # Prepare the message with status "success"
    message = {
        "type": "grid_alert",
        "status": "success",
        "message": alert_message,
        "transformer_data": transformer_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # Track successful sends
    successful_connections = set()
    
    # Broadcast to all clients, but only to utility dashboard clients
    for connection_id in client_connections:
        # Check client type
        client_type = connection_manager.get_client_type(connection_id)
        
        # Only send to utility dashboard clients
        if client_type == "utility_dashboard":
            logger.info(f"Sending grid alert to utility dashboard client: {connection_id}")
            success = await connection_manager.send_message(connection_id, message)
            if success:
                successful_connections.add(connection_id)
        else:
            logger.info(f"Skipping grid alert for non-utility client (type: {client_type}): {connection_id}")
    
    logger.info(f"Grid alert broadcasted to {len(successful_connections)} utility dashboard clients")
    
    return successful_connections


async def get_agent_dfp_recommendation(client_id: str, transformer_data: Dict[str, Any]) -> str:
    """
    Get DFP recommendations from the agent.
    
    Args:
        client_id: The client ID
        transformer_data: Data about the transformer with stress
        
    Returns:
        The agent's response
    """
    logger.info(f"Getting DFP recommendations from agent for client {client_id}")
    
    try:
        # Get the orchestrator instance for this client
        orchestrator = ClientOrchestrator.get_instance(client_id)
        
        # Create a prompt for the agent
        prompt = (
            f"A grid stress alert has been detected for transformer {transformer_data['name']} "
            f"[{transformer_data['display_id']}]. The current load is {transformer_data['current_load_kwh']:.2f} kWh "
            f"({transformer_data['load_percentage']:.1f}% of capacity), and capacity breach is likely in "
            f"{transformer_data['time_estimate']} minutes.\n\n"
            f"Please use the dfp_search tool to get available Demand Flexibility Program (DFP) options. "
            f"Then analyze the options and recommend the best one for this specific situation. "
            f"Format your response as follows:\n\n"
            f"1. First, list the available DFP options with their details (name, description, rewards, penalties, etc.)\n"
            f"2. Then, recommend the best option for this specific situation based on the current load and time estimate\n"
            f"3. Ask if the admin would like to proceed with the recommended option"
        )
        
        logger.info(f"Created prompt for agent: {prompt[:100]}...")
        
        # Add the prompt to history as a user message with a special prefix
        orchestrator.history_manager.add_user_message(client_id, f"[SYSTEM QUERY] {prompt}")
        
        # Process the query directly with the grid utility handler (similar to grid_utility_ws.py)
        try:
            # Get the route key for grid utility
            route_key = "grid_utility"
            
            # Find the handler config name associated with this route_key
            handler_config_name = None
            for route_cfg in orchestrator.app_config.query_router.routes:
                if route_cfg.route_key == route_key:
                    handler_config_name = route_cfg.handler_config_name
                    break
            
            if not handler_config_name:
                raise ValueError(f"No handler configuration found for route key: {route_key}")
            
            logger.info(f"Getting handler for config name: {handler_config_name}")
            
            # Get the handler directly
            query_handler = orchestrator._get_handler(handler_config_name)
            
            # Get the current chat history
            current_chat_history = orchestrator.history_manager.get_history(client_id)
            
            # Process the query with the handler
            logger.info("Processing query with grid utility handler...")
            ai_message = await query_handler.handle_query(prompt, current_chat_history)
            
            logger.info(f"Got AI response: {ai_message[:100]}...")
            
            # Add AI response to history
            orchestrator.history_manager.add_ai_message(client_id, ai_message)
            
            return ai_message
        except Exception as handler_error:
            logger.error(f"Error processing query with handler: {str(handler_error)}", exc_info=True)
            # Use fallback if handler fails
            fallback_message = get_fallback_dfp_recommendation(transformer_data)
            orchestrator.history_manager.add_ai_message(client_id, fallback_message)
            return fallback_message
    except Exception as e:
        logger.error(f"Error getting DFP recommendations: {str(e)}", exc_info=True)
        return get_fallback_dfp_recommendation(transformer_data)


def get_fallback_dfp_recommendation(transformer_data: Dict[str, Any]) -> str:
    """
    Get a fallback DFP recommendation with random selection between options.
    
    Args:
        transformer_data: Data about the transformer with stress
        
    Returns:
        A hardcoded DFP recommendation
    """
    logger.info("Using fallback DFP recommendation")
    
    # Randomly select which DFP option to recommend
    recommended_option = random.choice(["DDR", "EDR"])
    
    if recommended_option == "DDR":
        recommendation_text = f"I recommend Option 1 – Dynamic Demand Response (DDR) for immediate grid relief. The current situation at {transformer_data['name']} shows a load of {transformer_data['current_load_kwh']:.2f} kWh ({transformer_data['load_percentage']:.1f}% of capacity), which requires a rapid but moderate response. DDR is ideal for this scenario as it can be quickly activated and provides immediate relief without excessive disruption."
        option_number = "1"
        option_name = "Dynamic Demand Response (DDR)"
    else:
        recommendation_text = f"I recommend Option 2 – Emergency Demand Reduction (EDR) for immediate grid relief. The current situation at {transformer_data['name']} shows a load of {transformer_data['current_load_kwh']:.2f} kWh ({transformer_data['load_percentage']:.1f}% of capacity), which requires a significant and immediate response. EDR is designed for critical situations like this and can provide the necessary load reduction quickly."
        option_number = "2"
        option_name = "Emergency Demand Reduction (EDR)"
    
    return f"""Based on the grid stress alert for {transformer_data['name']} [{transformer_data['display_id']}], here are the available Demand Flexibility Program (DFP) options:

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

🔎{recommendation_text}

Would you like to proceed with activating the {option_name} program?""" 