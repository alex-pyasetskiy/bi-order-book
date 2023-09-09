import json
import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.connection import MANAGER
log = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/", response_description="Server status"
)
async def root():
    return "OK"


@router.post("/register")
def create_client_id():
    result = str(MANAGER.register_client())
    return JSONResponse(
            status_code=status.HTTP_201_CREATED, content=json.dumps(result)
        )
