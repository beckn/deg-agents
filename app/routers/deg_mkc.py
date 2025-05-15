from fastapi import APIRouter
import logging

router = APIRouter(prefix="/deg-mkc", tags=["deg-mkc"])
logger = logging.getLogger(__name__)


@router.get("")
async def deg_mkc():
    """
    Webhook endpoint
    """
    res = {"status": "ok", "message": "Server is up and running"}
    logger.info(f"DEG MKC Response: {res}")
    return res
