from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.core.orchestrator import ClientOrchestrator  # Import the orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint that accepts query and client_id,
    then processes it through the ClientOrchestrator.
    """
    if not request.query or not request.client_id:
        raise HTTPException(status_code=400, detail="Query and client_id are required.")

    try:
        # Get or create the orchestrator instance for this client
        orchestrator = ClientOrchestrator.get_instance(request.client_id)

        # Process the query
        ai_message = await orchestrator.process_query(request.query)

        return ChatResponse(
            status="success",
            query=request.query,
            client_id=request.client_id,
            message=ai_message,
        )
    except FileNotFoundError as e:  # For config loading issues
        print(f"Configuration Error: {e}")
        raise HTTPException(status_code=500, detail=f"Server configuration error: {e}")
    except ImportError as e:  # For dynamic loading issues
        print(f"Import Error during handler/tool loading: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Server setup error: failed to load a component: {e}",
        )
    except ValueError as e:  # For config validation or missing keys
        print(f"Value Error during setup: {e}")
        raise HTTPException(
            status_code=500, detail=f"Server configuration or setup error: {e}"
        )
    except NotImplementedError as e:  # For features not yet implemented
        print(f"NotImplementedError: {e}")
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        # Generic error handler for unexpected issues
        print(f"An unexpected error occurred for client {request.client_id}: {e}")
        # import traceback
        # traceback.print_exc() # For detailed debugging
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {e}"
        )


# Optional: Endpoint to clear a specific client's state (for debugging/testing)
@router.delete("/{client_id}/clear_state", status_code=204)
async def clear_client_state(client_id: str):
    """
    Clears the cached orchestrator instance and chat history for a specific client.
    Useful for testing or resetting a client's session.
    """
    ClientOrchestrator.clear_client_instance(client_id)
    # Also clear history from the global manager
    from app.core.history_manager import chat_history_manager

    chat_history_manager.clear_history(client_id)
    print(f"State and history cleared for client_id: {client_id}")
    return None
