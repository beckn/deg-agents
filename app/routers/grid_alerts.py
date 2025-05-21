from fastapi import APIRouter, BackgroundTasks, Depends
from typing import Dict, Any
import logging
import random
import asyncio
from app.core.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["grid_alerts"])

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
    
    # Format the transformer ID for display (e.g., TX005)
    display_id = f"TX{transformer_id:03d}" if transformer_id else "Unknown"
    
    # Generate a random time estimate between 25-35 minutes
    time_estimate = random.randint(25, 35)
    
    # Format the alert message
    alert_message = f"⚠️ Grid Stress Detected at Central Feeder Hub [{display_id}] – Capacity Breach Likely in {time_estimate} Minutes."
    
    # Prepare transformer data for the client
    transformer_data = {
        "transformer_id": transformer_id,
        "display_id": display_id,
        "name": transformer_name,
        "max_capacity_kw": transformer.get("max_capacity_KW"),
        "current_load_kwh": data.get("totalBaseKWh", 0),
        "time_estimate": time_estimate,
        "substation": transformer.get("substation", {}).get("name")
    }
    
    # Broadcast the alert in the background to avoid blocking the response
    background_tasks.add_task(broadcast_grid_alert, alert_message, transformer_data)
    
    return {"status": "success", "message": "Alert broadcasted to connected clients"}


async def broadcast_grid_alert(alert_message: str, transformer_data: Dict[str, Any]):
    """
    Broadcasts a grid alert to all connected WebSocket clients.
    """
    # Get all client connections
    client_connections = connection_manager.get_all_connections()
    
    # Prepare the message
    message = {
        "type": "grid_alert",
        "status": "alert",
        "message": alert_message,
        "transformer_data": transformer_data
    }
    
    # Broadcast to all clients
    for connection_id in client_connections:
        await connection_manager.send_message(connection_id, message)
    
    logger.info(f"Grid alert broadcasted to {len(client_connections)} clients")
    
    # Wait a few seconds before sending DFP options
    await asyncio.sleep(3)
    
    # Send DFP options to all clients
    await broadcast_dfp_options(transformer_data)


async def broadcast_dfp_options(transformer_data: Dict[str, Any]):
    """
    Broadcasts DFP options to all connected clients.
    """
    # Get all client connections
    client_connections = connection_manager.get_all_connections()
    
    # Get DFP options (hardcoded for now)
    dfp_options = get_dfp_options(transformer_data)
    
    # Format the options message
    options_message = "Based on the current stress levels, here are the available Demand Flexibility Program (DFP) options:\n\n"
    
    for i, option in enumerate(dfp_options, 1):
        options_message += f"Option {i}: {option['name']}\n"
        options_message += f"{option['description']}\n"
        options_message += f"Reward: {option['reward']}\n"
        options_message += f"Bonus: {option['bonus']}\n"
        options_message += f"Penalty: {option['penalty']}\n"
        options_message += f"Category: {option['category']}\n"
        options_message += f"Minimum Load: {option['minimum_load']} kW\n\n"
    
    # Prepare the message
    message = {
        "type": "dfp_options",
        "status": "success",
        "message": options_message,
        "options": dfp_options
    }
    
    # Broadcast to all clients
    for connection_id in client_connections:
        await connection_manager.send_message(connection_id, message)
    
    logger.info(f"DFP options broadcasted to {len(client_connections)} clients")
    
    # Wait a few seconds before sending recommendation
    await asyncio.sleep(2)
    
    # Send recommendation to all clients
    await broadcast_dfp_recommendation(transformer_data)


async def broadcast_dfp_recommendation(transformer_data: Dict[str, Any]):
    """
    Broadcasts DFP recommendation to all connected clients.
    """
    # Get all client connections
    client_connections = connection_manager.get_all_connections()
    
    # Get recommended option (hardcoded for now)
    recommended_option = get_recommended_option(transformer_data)
    
    # Format the recommendation message
    recommendation_message = f"🔎I recommend Option {recommended_option} – Dynamic Demand Response (DDR) for immediate grid relief. Would you like to proceed?"
    
    # Prepare the message
    message = {
        "type": "dfp_recommendation",
        "status": "success",
        "message": recommendation_message,
        "recommended_option": recommended_option
    }
    
    # Broadcast to all clients
    for connection_id in client_connections:
        await connection_manager.send_message(connection_id, message)
    
    logger.info(f"DFP recommendation broadcasted to {len(client_connections)} clients")


def get_dfp_options(transformer_data: Dict[str, Any]) -> list:
    """
    Returns a list of DFP options based on transformer data.
    Currently returns hardcoded options.
    """
    # In a real implementation, this would query a database or service
    # For now, we'll return hardcoded options
    return [
        {
            "id": 1,
            "name": "Dynamic Demand Response (DDR)",
            "description": "Dynamic Demand Response (DDR) rewards participants who can rapidly shift or curtail electricity usage during frequent, short-notice events. Participants receive the moderately high per-event compensation due to their ability to reliably and promptly adjust energy consumption patterns, significantly aiding grid stability and renewable energy integration.",
            "reward": "$3–4.5 per kWh shifted",
            "bonus": "15% extra if >90% compliance monthly",
            "penalty": "15% reduction in incentives if compliance <75%",
            "category": "Residential",
            "minimum_load": 5
        },
        {
            "id": 2,
            "name": "Emergency Demand Reduction (EDR)",
            "description": "Emergency Demand Reduction (EDR) is designed for consumers who can rapidly curtail significant energy use during critical, rare grid emergencies. These are infrequent but urgent events requiring immediate action. Participants are compensated significantly for availability but face substantial penalties for non-compliance due to critical grid dependence.",
            "reward": "$250/year per kW available",
            "bonus": "$10.00 per kWh curtailed during events",
            "penalty": "50% annual availability fee reduction per missed event",
            "category": "Residential",
            "minimum_load": 5
        }
    ]


def get_recommended_option(transformer_data: Dict[str, Any]) -> int:
    """
    Returns the recommended DFP option based on transformer data.
    Currently always returns option 1.
    """
    # In a real implementation, this would use more sophisticated logic
    # For now, always recommend option 1
    return 1 