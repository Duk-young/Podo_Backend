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
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from ..models.WineModel import WineModel
from typing import List, Optional
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
    keyword: str = "",
    tags: list[str] = Query(None),
):
    # TODO sorting 방식
    toSkip = num * (page - 1)
    wines = None
    if len(tags) == 0:
        wines = (
            request.app.mongodb["wine"]
            .find(
                {
                    "$and": [
                        {"price": {"$gte": minPrice}},
                        {"price": {"$lte": maxPrice}},
                        {"rating": {"$gte": minRating}},
                        {"isDeleted": False},
                    ],
                    "name": {"$regex": keyword},
                },
                {"_id": 0},
            )
            .sort("_id", -1)
            .skip(toSkip)
            .limit(num)
        )
    else:
        wines = (
            request.app.mongodb["wine"]
            .find(
                {
                    "$and": [
                        {"price": {"$gte": minPrice}},
                        {"price": {"$lte": maxPrice}},
                        {"rating": {"$gte": minRating}},
                        {"isDeleted": False},
                        {"tags": {"$in": tags}},
                    ],
                    "name": {"$regex": keyword},
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
    wines = request.app.mongodb["wine"].find({}, {"_id": 0})
    docs = await wines.to_list(None)
    return {"totalWines": len(docs)}


@router.get("/{wineID}")
async def get_wine(request: Request, wineID: int):
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="No such wine exists")
        response.status_code = 404
        return response
    return wine


@router.get("/recommended")
async def get_recommended_wines(request: Request, userID: int = -1, num: int = 10):
    # TODO
    return 0


@router.post("")
async def post_wine(
    request: Request, userID: int = -1, wineInfo: WineModel = Body(...)
):
    json_wineInfo = jsonable_encoder(wineInfo)
    print(json_wineInfo)
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2:
        response = JSONResponse(content="User is not authorized for this action")
        response.status_code = 401
        return response
    newWineID = await request.app.mongodb["auto_incrementer"].find_one_and_update(
        {"_id": "wine"}, {"$inc": {"index": 1}}, {"index": 1}
    )
    newWine = await request.app.mongodb["wine"].insert_one(
        {
            "wineID": newWineID["index"],
            "tags": json_wineInfo["tags"],
            "name": json_wineInfo["name"],
            "images": json_wineInfo["images"],
            "lightness": json_wineInfo["lightness"],
            "smoothness": json_wineInfo["smoothness"],
            "sweetness": json_wineInfo["sweetness"],
            "softness": json_wineInfo["softness"],
            "abv": json_wineInfo["abv"],
            "price": json_wineInfo["price"],
            "region": json_wineInfo["region"],
            "closure": json_wineInfo["closure"],
            "grapes": json_wineInfo["grapes"],
            "rating": json_wineInfo["rating"],
            "winery": json_wineInfo["winery"],
            "description": json_wineInfo["description"],
            "views": 0,
            "likes": [],
            "isDeleted": False,
            "createdAt": json_wineInfo["createdAt"],
            "lastUpdatedAt": json_wineInfo["lastUpdatedAt"],
        }
    )
    if newWine == None:
        response = JSONResponse(
            content="An error occurred while creating new wine object"
        )
        response.status_code = 400
        return response
    else:
        response = JSONResponse(content="Successfully created new wine")
        response.status_code = 201
        return response


@router.post("/restore/{wineID}")
async def restore_wine(request: Request, wineID: int = -1, userID: int = -1):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2:
        response = JSONResponse(content="User is not authorized for this action")
        response.status_code = 401
        return response
    wine = await request.app.mongodb["wine"].find_one_and_update(
        {"wineID": wineID}, {"$set": {"isDeleted": False}}, {"_id": 0}
    )
    if wine != None:
        return {
            "wineID": wine["wineID"],
            "isDeleted": wine["isDeleted"],
            "lastUpdatedAt": wine["lastUpdatedAt"],
        }
    return "Failed to restore wine."


@router.put("/{wineID}")
async def update_wine(
    request: Request,
    userID: int = -1,
    wineID: int = -1,
    wineInfo: WineModel = Body(...),
):
    json_wineInfo = jsonable_encoder(wineInfo)
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2:
        response = JSONResponse(content="User is not authorized for this action")
        response.status_code = 401
        return response
    wine = await request.app.mongodb["wine"].find_one_and_update(
        {"wineID": wineID},
        {
            "$set": {
                "tags": json_wineInfo["tags"],
                "name": json_wineInfo["name"],
                "images": json_wineInfo["images"],
                "lightness": json_wineInfo["lightness"],
                "smoothness": json_wineInfo["smoothness"],
                "sweetness": json_wineInfo["sweetness"],
                "softness": json_wineInfo["softness"],
                "abv": json_wineInfo["abv"],
                "price": json_wineInfo["price"],
                "region": json_wineInfo["region"],
                "closure": json_wineInfo["closure"],
                "grapes": json_wineInfo["grapes"],
                "winery": json_wineInfo["winery"],
                "description": json_wineInfo["description"],
                "lastUpdatedAt": json_wineInfo["lastUpdatedAt"],
            }
        },
        {"_id": 0},
    )
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    else:
        return wine


@router.delete("/{wineID}")
async def delete_wine(request: Request, wineID: int = -1, userID: int = -1):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    if requester == None or requester["status"] != 2:
        response = JSONResponse(
            content="No such user exists or user is not authorized for this action"
        )
        response.status_code = 401
        return response
    wine = await request.app.mongodb["wine"].find_one_and_update(
        {"wineID": wineID}, {"$set": {"isDeleted": True}}, {"_id": 0}
    )
    if wine != None:
        return {
            "wineID": wine["wineID"],
            "isDeleted": wine["isDeleted"],
            "lastUpdatedAt": wine["lastUpdatedAt"],
        }
    return "Failed to restore wine."
