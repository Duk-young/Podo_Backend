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
from typing import List, Optional
from tempfile import TemporaryFile
from datetime import datetime

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
    },
)


@router.get("/total")
async def get_total_users(request: Request):
    users = request.app.mongodb["user"].find({}, {"_id": 0})
    docs = await users.to_list(None)
    return {"totalUsers": len(docs)}


@router.get("")
async def get_users(request: Request, userID: int = -1, num: int = 100, page: int = 1):
    toSkip = num * (page - 1)
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
    users = (
        request.app.mongodb["user"]
        .find({}, {"_id": 0})
        .sort("_id", -1)
        .skip(toSkip)
        .limit(num)
    )
    docs = await users.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content="No user exists in DB")
        response.status_code = 204
        return response
    return docs


@router.get("/{userID}")
async def get_user(request: Request, userID: int = -1, requesterID: int = -1):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": requesterID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="RequesterID : No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2:
        response = JSONResponse(content="Requester is not authorized for this action")
        response.status_code = 401
        return response
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="userID : No such user exists")
        response.status_code = 404
        return response
    return user


@router.get("/username-duplicate-check")
async def username_duplicate_check(request: Request, username: str = ""):
    user = request.app.mongodb["user"].find_one({"username": username}, {"_id": 0})
    if user == None:
        return {"username": username, "duplicate": False}
    return {"username": username, "duplicate": True}


@router.get("/email-duplicate-check")
async def username_duplicate_check(request: Request, email: str = ""):
    user = request.app.mongodb["user"].find_one({"email": email}, {"_id": 0})
    if user == None:
        return {"email": email, "duplicate": False}
    return {"email": email, "duplicate": True}


@router.get("/my-wine-reviews")
async def get_user_wine_review(
    request: Request, userID: int = -1, num: int = 20, page: int = 1
):
    toSkip = num * (page - 1)
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    reviews = (
        request.app.mongodb["review"]
        .find({"userID": userID}, {"_id": 0})
        .skip(toSkip)
        .limit(num)
    )
    docs = await reviews.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content="No more reviews to fetch")
        response.status_code = 204
        return response
    return docs


@router.get("/my-winelist-comment")
async def get_user_winelist_review(
    request: Request, userID: int = -1, num: int = 20, page: int = 1
):
    # 보류
    toSkip = num * (page - 1)
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    reviews = (
        request.app.mongodb["review"]
        .find({"userID": userID}, {"_id": 0})
        .skip(toSkip)
        .limit(num)
    )
    docs = await reviews.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content="No more reviews to fetch")
        response.status_code = 204
        return response
    return docs


@router.post("")
async def post_user(request: Request, userInfo: UserModel = Body(...)):
    json_userInfo = jsonable_encoder(userInfo)
    newUserID = await request.app.mongodb["auto_incrementer"].find_one_and_update(
        {"_id": "user"}, {"$inc": {"index": 1}}, {"index": 1}
    )
    json_userInfo["userID"] = newUserID["index"]
    newUser = await request.app.mongodb["user"].insert_one(json_userInfo)
    if newUser == None:
        response = JSONResponse(content="RequesterID : No such user exists")
        response.status_code = 404
        return response
    response = JSONResponse(
        content={
            "userID": newUserID["index"],
            "createdAt": json_userInfo["createdAt"],
        }
    )
    response.status_code = 201
    return response


@router.post("/{userID}/like-wine")
async def like_wine(request: Request, userID: int = -1, wineID: int = -1):
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if wineID not in user["likedWines"]:
        user = await request.app.mongodb["user"].find_one_and_update(
            {"userID": userID},
            {
                "$push": {"likedWines": wineID},
                "$set": {
                    "lastUpdatedAt": datetime.now()
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S"),
                },
            },
            {"_id": 0},
            return_document=ReturnDocument.AFTER,
        )
    else:
        user = await request.app.mongodb["user"].find_one_and_update(
            {"userID": userID},
            {
                "$pull": {"likedWines": wineID},
                "$set": {
                    "lastUpdatedAt": datetime.now()
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S"),
                },
            },
            {"_id": 0},
            return_document=ReturnDocument.AFTER,
        )
    if user == None:
        response = JSONResponse(content="An error occurred while updating user")
        response.status_code = 404
        return response
    return {
        "userID": user["userID"],
        "likedWines": user["likedWines"],
        "lastUpdatedAt": user["lastUpdatedAt"],
    }


@router.post("/{userID}/like-winelist")
async def like_winelist(request: Request, userID: int = -1, winelistID: int = -1):
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if winelistID not in user["likedWinelists"]:
        user = await request.app.mongodb["user"].find_one_and_update(
            {"userID": userID},
            {
                "$push": {"likedWinelists": winelistID},
                "$set": {
                    "lastUpdatedAt": datetime.now()
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S"),
                },
            },
            {"_id": 0},
            return_document=ReturnDocument.AFTER,
        )
    else:
        user = await request.app.mongodb["user"].find_one_and_update(
            {"userID": userID},
            {
                "$pull": {"likedWinelists": winelistID},
                "$set": {
                    "lastUpdatedAt": datetime.now()
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S"),
                },
            },
            {"_id": 0},
            return_document=ReturnDocument.AFTER,
        )
    if user == None:
        response = JSONResponse(content="An error occurred while updating user")
        response.status_code = 404
        return response
    return {
        "userID": user["userID"],
        "likedWinelists": user["likedWinelists"],
        "lastUpdatedAt": user["lastUpdatedAt"],
    }


@router.post("/{userID}/tags")
async def like_tags(
    request: Request,
    userID: int = -1,
    tags: list[str] = Query(None),
):
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    user = await request.app.mongodb["user"].find_one_and_update(
        {"userID": userID},
        {
            "$set": {
                "lastUpdatedAt": datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
                "tags": tags,
            },
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if user == None:
        response = JSONResponse(content="An error occurred while updating user")
        response.status_code = 404
        return response
    return {
        "userID": user["userID"],
        "tags": user["tags"],
        "lastUpdatedAt": user["lastUpdatedAt"],
    }


@router.post("/{userID}/follow")
async def like_user(
    request: Request,
    userID: int = -1,
    targetUserID: int = -1,
    followOption: str = "following",
):
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    targetUser = await request.app.mongodb["user"].find_one(
        {"userID": targetUserID}, {"_id": 0}
    )
    if targetUser == None:
        response = JSONResponse(content="No such target user exists")
        response.status_code = 404
        return response
    if followOption == "following":
        if targetUserID in user["followings"]:
            user = await request.app.mongodb["user"].find_one_and_update(
                {"userID": userID},
                {
                    "$push": {"followings": targetUserID},
                    "$set": {
                        "lastUpdatedAt": datetime.now()
                        .astimezone()
                        .strftime("%Y-%m-%d %H:%M:%S"),
                    },
                },
                {"_id": 0},
                return_document=ReturnDocument.AFTER,
            )
        else:
            user = await request.app.mongodb["user"].find_one_and_update(
                {"userID": userID},
                {
                    "$pull": {"followings": targetUserID},
                    "$set": {
                        "lastUpdatedAt": datetime.now()
                        .astimezone()
                        .strftime("%Y-%m-%d %H:%M:%S"),
                    },
                },
                {"_id": 0},
                return_document=ReturnDocument.AFTER,
            )
    else:
        if targetUserID in user["followers"]:
            user = await request.app.mongodb["user"].find_one_and_update(
                {"userID": userID},
                {
                    "$push": {"followers": targetUserID},
                    "$set": {
                        "lastUpdatedAt": datetime.now()
                        .astimezone()
                        .strftime("%Y-%m-%d %H:%M:%S"),
                    },
                },
                {"_id": 0},
                return_document=ReturnDocument.AFTER,
            )
        else:
            user = await request.app.mongodb["user"].find_one_and_update(
                {"userID": userID},
                {
                    "$pull": {"followers": targetUserID},
                    "$set": {
                        "lastUpdatedAt": datetime.now()
                        .astimezone()
                        .strftime("%Y-%m-%d %H:%M:%S"),
                    },
                },
                {"_id": 0},
                return_document=ReturnDocument.AFTER,
            )
    if user == None:
        response = JSONResponse(content="An error occurred while updating user")
        response.status_code = 404
        return response
    if followOption == "following":
        return {
            "userID": user["userID"],
            "followings": user["followings"],
            "lastUpdatedAt": user["lastUpdatedAt"],
        }
    else:
        return {
            "userID": user["userID"],
            "followers": user["followers"],
            "lastUpdatedAt": user["lastUpdatedAt"],
        }


@router.put("/{userID}")
async def update_user(
    request: Request, userID: int = -1, userInfo: UserModel = Body(...)
):
    json_userInfo = jsonable_encoder(userInfo)
    update_user = await request.app.mongodb["user"].find_one_and_update(
        {"userID": userID},
        {
            "$set": {
                "username": json_userInfo["username"],
                "email": json_userInfo["email"],
                "profileImage": json_userInfo["profileImage"],
                "phone": json_userInfo["phone"],
                "gender": json_userInfo["gender"],
                "lastUpdatedAt": json_userInfo["lastUpdatedAt"],
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if update_user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    return {"userID": userID, "lastUpdateAt": json_userInfo["lastUpdatedAt"]}


@router.post("/{userID}/status")
async def update_user(
    request: Request, userID: int = -1, adminID: int = -1, level: int = 1
):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": adminID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="RequesterID : No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2:
        response = JSONResponse(content="Requester is not authorized for this action")
        response.status_code = 401
        return response
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="userID : No such user exists")
        response.status_code = 404
        return response
    update_user = await request.app.mongodb["user"].find_one_and_update(
        {"userID": userID},
        {
            "$set": {
                "status": level,
                "lastUpdatedAt": datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if update_user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    return {
        "userID": update_user["userID"],
        "adminID": adminID,
        "status": update_user["status"],
        "lastUpdateAt": update_user["lastUpdatedAt"],
    }


@router.delete("/{userID}")
async def delete_wine(request: Request, userID: int = -1, adminID: int = -1):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": adminID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="adminID : No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2:
        response = JSONResponse(content="adminID is not authorized for this action")
        response.status_code = 401
        return response
    user = await request.app.mongodb["user"].find_one_and_update(
        {"userID": userID},
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
    if user == None:
        response = JSONResponse(content="userID : No such user exists")
        response.status_code = 404
        return response
    return {
        "userID": userID,
        "isDeleted": user["isDeleted"],
        "lastUpdatedAt": user["lastUpdatedAt"],
    }