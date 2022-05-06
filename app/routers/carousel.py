from fastapi import (
    APIRouter,
    Body,
    Request,
    HTTPException,
    status,
    File,
    UploadFile,
    Form,
)
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from typing import List
from PIL import Image
from tempfile import TemporaryFile

router = APIRouter(
    prefix="/carousel",
    tags=["carousel"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
        204: {"description": "No content found"},
    },
)


@router.get("")
async def update_carousel(request: Request, adminID: int = -1):
    return 0
