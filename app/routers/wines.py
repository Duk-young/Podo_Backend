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
import sys
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from ..models.WineModel import WineModel
from ..models.TagsModel import TagsModel
from typing import List
from tempfile import TemporaryFile

router = APIRouter(
    prefix="/wines",
    tags=["wines"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
    },
)


@router.get("/search")
async def search_wines(
    request: Request,
    num: int = 10,
    page: int = 1,
    minPrice: float = 0,
    maxPrice: float = sys.maxsize,
    minRating: float = 0,
    tags=TagsModel,
):
    toSkip = num * (page - 1)
    wines = (
        request.app.mongodb["wines"]
        .find(
            {
                "$and": [
                    {"price": {"$gte": minPrice}},
                    {"price": {"$lte": maxPrice}},
                    {"rating": {"$gte": minRating}},
                ]
            },
            {"_id": 0},
        )
        .sort("_id", -1)
        .skip(toSkip)
        .limit(num)
    )
    docs = await wines.to_list(None)
    return docs


@router.get("/total")
async def total_wines(request: Request):
    wines = request.app.mongodb["wines"].find({}, {"_id": 0})
    docs = await wines.to_list(None)
    return len(docs)


@router.get("/{wineID}")
async def get_wine(request: Request, wineID: int):
    wine = await request.app.mongodb["wines"].find_one({"wineID": wineID}, {"_id": 0})
    return wine


@router.get("/recommended")
async def get_recommended_wines(request: Request, userID: int = -1, num: int = 10):
    # TODO
    return 0


@router.post("/")
async def post_wine(request: Request):
    # TODO
    return 0


@router.post("/restore/{wineID}")
async def restore_wine(request: Request, wineID: int):
    wine = await request.app.mongodb["wines"].find_one_and_update(
        {"wineID": wineID}, {"$set": {"isDeleted": False}}, {"_id": 0}
    )
    if len(wine) != 0:
        return {
            "wineID": wine["wineID"],
            "isDeleted": wine["isDeleted"],
            "lastUpdatedAt": wine["lastUpdatedAt"],
        }
    return "Failed to restore wine."
