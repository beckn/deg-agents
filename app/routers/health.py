from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Health check endpoint to verify if the server is running
    """
    return {"status": "ok", "message": "Server is up and running"}
