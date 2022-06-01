import json
from fastapi import (
    APIRouter,
    Body,
    Query,
    Request,
    HTTPException,
    status,
    File,
    UploadFile,
    Form,
)
import sys
from fastapi.responses import JSONResponse
from pymongo import ReturnDocument
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_200_OK, HTTP_201_CREATED


router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
        204: {"description": "No content found"},
    },
)


@router.get("/list")
async def get_listof_tags(request: Request):
    # TODO API DOCS
    tags = await request.app.mongodb["tag"].find_one({"_id": "main"}, {"_id": 0})
    if tags == None:
        response = JSONResponse(content=[])
        response.status_code = 200
        return response
    return tags["names"]
