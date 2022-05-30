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
import re

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
    tags: list[str] = Query([]),
    sort: int = 1,
):
    # TODO 정렬
    toSkip = num * (page - 1)
    winelists = None
    if len(tags) == 0:
        winelists = (
            request.app.mongodb["winelist"].aggregate(
                [  # {"$sort": {sortingOption: -1}},
                    {
                        "$match": {
                            "isDeleted": False,
                            "title": {"$regex": keyword, "$options": "i"},
                        },
                    },
                    {"$sort": {"_id": -1}},
                    {"$skip": toSkip},
                    {"$limit": num},
                    {  # lookup for reviews
                        "$lookup": {
                            "from": "wine",
                            "localField": "wines.wineID",
                            "foreignField": "wineID",
                            "pipeline": [
                                {
                                    "$project": {
                                        "_id": 0,
                                        "wineID": 1,
                                        "name": 1,
                                        "images": 1,
                                    }
                                }
                            ],
                            "as": "wines",
                        }
                    },
                    {  # lookup for user
                        "$lookup": {
                            "from": "user",
                            "localField": "userID",
                            "foreignField": "userID",
                            "pipeline": [
                                {
                                    "$project": {
                                        "_id": 0,
                                        "username": 1,
                                        "profileImage": 1,
                                    }
                                }
                            ],
                            "as": "author",
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                        }
                    },
                ]
            )
            # .sort("_id", -1)
            # .skip(toSkip)
            # .limit(num)
        )
    else:
        regexTags = []
        for tag in tags:
            regexTags.append(re.compile(tag, re.IGNORECASE))
        winelists = request.app.mongodb["winelist"].aggregate(
            [  # {"$sort": {sortingOption: -1}},
                {
                    "$match": {
                        "isDeleted": False,
                        "title": {"$regex": keyword, "$options": "i"},
                        "tags": {"$all": regexTags},
                    },
                },
                {"$sort": {"_id": -1}},
                {"$skip": toSkip},
                {"$limit": num},
                {  # lookup for reviews
                    "$lookup": {
                        "from": "wine",
                        "localField": "wines.wineID",
                        "foreignField": "wineID",
                        "pipeline": [
                            {
                                "$project": {
                                    "_id": 0,
                                    "wineID": 1,
                                    "name": 1,
                                    "images": 1,
                                }
                            }
                        ],
                        "as": "wines",
                    }
                },
                {  # lookup for user
                    "$lookup": {
                        "from": "user",
                        "localField": "userID",
                        "foreignField": "userID",
                        "pipeline": [
                            {
                                "$project": {
                                    "_id": 0,
                                    "username": 1,
                                    "profileImage": 1,
                                }
                            }
                        ],
                        "as": "author",
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                    }
                },
            ]
        )
    docs = await winelists.to_list(None)
    for doc in docs:
        doc["username"] = doc["author"][0]["username"]
        doc["profileImage"] = doc["author"][0]["profileImage"]
        doc.pop("author")
    return docs


@router.get("/recommended")
async def get_recommended_winelists(request: Request, userID: int = -1, num: int = 5):
    # TODO
    return 0


@router.post("")
async def post_winelist(request: Request, winelistInfo: WinelistModel = Body(...)):
    json_winelistInfo = jsonable_encoder(winelistInfo)
    print(json_winelistInfo)
    requester = await request.app.mongodb["user"].find_one(
        {"userID": json_winelistInfo["userID"]}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if requester["status"] < 1:
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


@router.get("/{winelistID}")
async def get_winelist(request: Request, winelistID: int = -1):
    winelist = request.app.mongodb["winelist"].aggregate(
        [
            {
                "$match": {
                    "isDeleted": False,
                    "winelistID": winelistID,
                },
            },
            {"$unwind": "$wines"},
            {  # lookup for wine
                "$lookup": {
                    "from": "wine",
                    "localField": "wines.wineID",
                    "foreignField": "wineID",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                                "wineID": 1,
                                "name": 1,
                                "images": 1,
                            }
                        }
                    ],
                    "as": "wines.wineInfo",
                }
            },
            {
                "$group": {
                    "_id": {"winelistID": "$winelistID"},
                    "userID": {"$first": "$userID"},
                    "title": {"$first": "$title"},
                    "thumbnailImage": {"$first": "$thumbnailImage"},
                    "tags": {"$first": "$tags"},
                    "content": {"$first": "$content"},
                    "wines": {
                        "$push": {
                            "wineID": {"$first": "$wines.wineInfo.wineID"},
                            "name": {"$first": "$wines.wineInfo.name"},
                            "images": {"$first": "$wines.wineInfo.images"},
                            "sommelierComment": "$wines.sommelierComment",
                        }
                    },
                    "isDeleted": {"$first": "$isDeleted"},
                    "createdAt": {"$first": "$createdAt"},
                    "lastUpdatedAt": {"$first": "$lastUpdatedAt"},
                    "views": {"$first": "$views"},
                    "likes": {"$first": "$likes"},
                    "winelistID": {"$first": "$winelistID"},
                }
            },
            {  # lookup for user
                "$lookup": {
                    "from": "user",
                    "localField": "userID",
                    "foreignField": "userID",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                                "username": 1,
                                "profileImage": 1,
                            }
                        },
                    ],
                    "as": "author",
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "username": {"$first": "$author.username"},
                    "profileImage": {"$first": "$author.profileImage"},
                    "userID": 1,
                    "thumbnailImage": 1,
                    "tags": 1,
                    "content": 1,
                    "wines": 1,
                    "isDeleted": 1,
                    "createdAt": 1,
                    "lastUpdatedAt": 1,
                    "views": 1,
                    "likes": 1,
                    "winelistID": 1,
                }
            },
        ]
    )
    if winelist == None:
        response = JSONResponse(content="No such winelist exists")
        response.status_code = 404
        return response
    doc = await winelist.to_list(None)
    doc = doc[0]
    # doc["username"] = doc["author"][0]["username"]
    # doc["profileImage"] = doc["author"][0]["profileImage"]
    # doc.pop("author")
    return doc


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


@router.post("/winelist-population")
async def populate_winelist(request: Request, num: int = 50):
    return 0
