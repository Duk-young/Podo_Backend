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
from ..models.UserModel import UserModel
from ..models.WinelistModel import WinelistModel
from typing import List, Optional
from tempfile import TemporaryFile
from datetime import datetime

router = APIRouter(
    prefix="/winelists",
    tags=["winelists"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
    },
)


@router.get("/total")
async def get_total_winelists(request: Request):
    winelists = request.app.mongodb["winelist"].find({}, {"_id": 0})
    docs = await winelists.to_list(None)
    return {"totalWinelists": len(docs)}


@router.get("/search")
async def search_winelists(
    request: Request,
    keyword: str = "",
    num: int = 10,
    page: int = 1,
    minRating: int = 0,
    tags: list[str] = Query(None),
    sort: int = 1,
):
    toSkip = num * (page - 1)
    winelists = None
    if len(tags) == 0:
        winelists = (
            request.app.mongodb["winelist"]
            .find(
                {
                    "$and": [
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
        winelists = (
            request.app.mongodb["winelist"]
            .find(
                {
                    "$and": [
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
        docs = await winelists.to_list(None)
        return docs


@router.get("/{winelistID}")
async def get_winelist(request: Request, winelistID: int = -1):
    winelist = await request.app.mongodb["winelist"].find_one(
        {"winelistID": winelistID}, {"_id": 0}
    )
    if winelist == None:
        response = JSONResponse(content="No such winelist exists")
        response.status_code = 404
        return response
    return winelist


@router.get("/recommended")
async def get_recommended_winelists(request: Request, userID: int = -1, num: int = 5):
    # TODO
    return 0


@router.post("")
async def post_winelist(
    request: Request, userID: int = -1, winelistInfo: WinelistModel = Body(...)
):
    json_winelistInfo = jsonable_encoder(winelistInfo)
    print(json_winelistInfo)
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
    newWinelistID = await request.app.mongodb["auto_incrementer"].find_one_and_update(
        {"_id": "winelist"}, {"$inc": {"index": 1}}, {"index": 1}
    )
    json_winelistInfo["winelistID"] = newWinelistID["index"]
    newWinelist = await request.app.mongodb["winelist"].insert_one(json_winelistInfo)
    if newWinelist == None:
        response = JSONResponse(
            content="An error occurred while creating new winelist object"
        )
        response.status_code = 400
        return response
    else:
        response = JSONResponse(
            content={
                "winelistID": newWinelistID["index"],
                "createdAt": json_winelistInfo["createdAt"],
            }
        )
        response.status_code = 201
        return response


@router.post("/restore/{winelistID}")
async def restore_winelist(request: Request, winelistID: int = -1, userID: int = -1):
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
    winelist = await request.app.mongodb["winelist"].find_one_and_update(
        {"winelistID": winelistID},
        {
            "$set": {
                "isDeleted": False,
                "lastUpdatedAt": datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if winelist != None:
        return {
            "winelistID": winelist["winelistID"],
            "isDeleted": winelist["isDeleted"],
            "lastUpdatedAt": winelist["lastUpdatedAt"],
        }
    return "Failed to restore winelist."


@router.put("/{winelistID}")
async def update_wine(
    request: Request,
    userID: int = -1,
    winelistID: int = -1,
    winelistInfo: WinelistModel = Body(...),
):
    json_winelistInfo = jsonable_encoder(winelistInfo)
    requester = await request.app.mongodb["user"].find_one(
        {"userID": json_winelistInfo["userID"]}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    winelist = await request.app.mongodb["winelist"].find_one(
        {"userID": json_winelistInfo["userID"], "winelistID": winelistID}, {"_id": 0}
    )
    if winelist == None:
        response = JSONResponse(content="User is not authorized for this action")
        response.status_code = 401
        return response
    winelist = await request.app.mongodb["winelist"].find_one_and_update(
        {"winelistID": winelistID},
        {
            "$set": {
                "title": json_winelistInfo["title"],
                "images": json_winelistInfo["images"],
                "tags": json_winelistInfo["tags"],
                "content": json_winelistInfo["content"],
                "wines": json_winelistInfo["wines"],
                "lastUpdatedAt": (
                    datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
                ),
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if winelist == None:
        response = JSONResponse(
            content="WinelistID is invalid. No such winelist exists in DB"
        )
        response.status_code = 404
        return response
    else:
        return winelist


@router.delete("/{winelistID}")
async def delete_winelist(request: Request, winelistID: int = -1, userID: int = -1):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    winelist = await request.app.mongodb["winelist"].find_one(
        {"winelistID": winelistID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if winelist == None:
        response = JSONResponse(content="No such winelist exists")
        response.status_code = 404
        return response
    if userID != winelist["userID"] and requester["status"] != 2:
        response = JSONResponse(content="User is not authorized for this action")
        response.status_code = 401
        return response
    winelist = await request.app.mongodb["winelist"].find_one_and_update(
        {"winelistID": winelistID},
        {
            "$set": {
                "isDeleted": True,
                "lastUpdatedAt": datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if winelist != None:
        return {
            "winelistID": winelist["winelistID"],
            "isDeleted": winelist["isDeleted"],
            "lastUpdatedAt": winelist["lastUpdatedAt"],
        }
    return "Failed to restore winelist."