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
import httpx
import random
import time

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
        204: {"description": "No content found"},
    },
)


@router.get("/login")
async def user_login(request: Request, access_token: str = ""):
    # TODO 에러핸들링 / 로그인시 프로필사진 업뎃
    async with httpx.AsyncClient() as client:
        url = (
            "https://www.googleapis.com/oauth2/v1/userinfo?access_token=" + access_token
        )
        response = await client.get(url)
        response = response.json()
        print(response["email"])
        user = await request.app.mongodb["user"].find_one(
            {"email": response["email"]}, {"_id": 0}
        )
        print(user)
        if user == None:
            return {"userID": -1}
        return {
            "userID": user["userID"],
            "username": user["username"],
            "email": user["email"],
            "status": user["status"],
            "profileImage": response["picture"],
        }


@router.get("/total")
async def get_total_users(request: Request):
    users = request.app.mongodb["user"].find({}, {"_id": 0})
    if users == None:
        response = JSONResponse(content="No user found")
        response.status_code = 200
        return response
    docs = await users.to_list(None)
    return {"totalUsers": len(docs)}


@router.get("")
async def get_users_insensitive(
    request: Request, num: int = 50, page: int = 1, username: str = ""
):
    toSkip = num * (page - 1)
    users = (
        request.app.mongodb["user"]
        .find(
            {"username": {"$regex": username, "$options": "i"}},
            {
                "_id": 0,
                "userID": 1,
                "username": 1,
                "profileImage": 1,
                "status": 1,
                "tags": 1,
                "followings": 1,
                "followers": 1,
            },
        )
        .sort("_id", -1)
        .skip(toSkip)
        .limit(num)
    )
    docs = await users.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content="No user exists in DB")
        response.status_code = 200
        return response
    return docs


@router.get("/all-fields")
async def get_users_sensitive(
    request: Request, userID: int = -1, num: int = 100, page: int = 1
):
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
        response.status_code = 200
        return response
    return docs


@router.get("/username-duplicate-check")
async def username_duplicate_check(request: Request, username: str = ""):
    user = await request.app.mongodb["user"].find_one(
        {"username": username}, {"_id": 0}
    )
    if user == None:
        return {"username": username, "duplicate": False}
    return {"username": username, "duplicate": True}


@router.get("/email-duplicate-check")
async def email_duplicate_check(request: Request, email: str = ""):
    user = await request.app.mongodb["user"].find_one({"email": email}, {"_id": 0})
    print(user)
    if user == None:
        return {"email": email, "duplicate": False}
    return {"email": email, "duplicate": True}


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
        response = JSONResponse(content=[])
        response.status_code = 200
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


@router.get("{userID}/all-fields")
async def get_user(request: Request, userID: int = -1, requesterID: int = -1):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": requesterID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="RequesterID : No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2 and userID != requesterID:
        response = JSONResponse(content="Requester is not authorized for this action")
        response.status_code = 401
        return response
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="userID : No such user exists")
        response.status_code = 404
        return response
    return user


@router.get("/{userID}")
async def get_user(request: Request, userID: int = -1):
    user = await request.app.mongodb["user"].find_one(
        {"userID": userID},
        {
            "_id": 0,
            "userID": 1,
            "username": 1,
            "profileImage": 1,
            "status": 1,
            "likedWines": 1,
            "likedWinelists": 1,
            "tags": 1,
            "followings": 1,
            "followers": 1,
        },
    )
    if user == None:
        response = JSONResponse(content="userID : No such user exists")
        response.status_code = 404
        return response
    return user


@router.get("/{userID}/followings")
async def get_user_followings(request: Request, userID: int = -1):
    user = request.app.mongodb["user"].aggregate(
        [
            {"$match": {"userID": userID}},
            {
                "$lookup": {
                    "from": "user",
                    "localField": "followings",
                    "foreignField": "userID",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                                "userID": 1,
                                "username": 1,
                                "profileImage": 1,
                                "status": 1,
                            }
                        }
                    ],
                    "as": "followings",
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "userID": 1,
                    "username": 1,
                    "profileImage": 1,
                    "status": 1,
                    "followings": 1,
                }
            },
        ]
    )
    user = await user.to_list(None)
    if len(user) == 0:
        response = JSONResponse(content="userID : No such user exists")
        response.status_code = 404
        return response
    return user[0]


@router.get("/{userID}/followers")
async def get_user_followers(request: Request, userID: int = -1):
    user = request.app.mongodb["user"].aggregate(
        [
            {"$match": {"userID": userID}},
            {
                "$lookup": {
                    "from": "user",
                    "localField": "followers",
                    "foreignField": "userID",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                                "userID": 1,
                                "username": 1,
                                "profileImage": 1,
                                "status": 1,
                            }
                        }
                    ],
                    "as": "followers",
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "userID": 1,
                    "username": 1,
                    "profileImage": 1,
                    "status": 1,
                    "followers": 1,
                }
            },
        ]
    )
    user = await user.to_list(None)
    if len(user) == 0:
        response = JSONResponse(content="userID : No such user exists")
        response.status_code = 404
        return response
    return user[0]


@router.get("/{userID}/reviews")
async def get_user_wine_review(
    request: Request, userID: int = -1, num: int = 20, page: int = 1
):  # TODO likedBy -> likes 개수로 바꿔줘야함
    toSkip = num * (page - 1)
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    reviews = (
        request.app.mongodb["review"]
        .find({"userID": userID}, {"_id": 0, "comments": 0})
        .skip(toSkip)
        .limit(num)
    )
    docs = await reviews.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content=[])
        response.status_code = 200
        return response
    return docs


@router.get("/{userID}/reviewed-wines")
async def get_listof_user_reviewed_wine(
    request: Request, userID: int = -1, num: int = 20, page: int = 1
):
    # TODO 204 -> 200 [] DOCS UPDATE
    # TODO 와인 이미지들을 반환해야하는지?
    # TODO URL 추가해야 할 듯
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
        response = JSONResponse(content=[])
        response.status_code = 200
        return response
    wineIDs = []
    for doc in docs:
        wineIDs.append(doc["wineID"])
    wines = (
        request.app.mongodb["wine"]
        .find({"wineID": {"$in": wineIDs}}, {"_id": 0})
        .skip(toSkip)
        .limit(num)
    )
    docs = await wines.to_list(None)
    return docs


@router.get("/{userID}/liked-wines")
async def get_listof_user_liked_wine(
    request: Request, userID: int = -1, num: int = 20, page: int = 1
):
    # TODO 204 -> 200 []
    toSkip = num * (page - 1)
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    likedWines = user["likedWines"]
    wines = (
        request.app.mongodb["wine"]
        .find(
            {"wineID": {"$in": likedWines}, "isDeleted": False},
            {
                "_id": 0,
                "wineID": 1,
                "name": 1,
                "images": 1,
                "createdAt": 1,
                "lastUpdatedAt": 1,
            },
        )
        .skip(toSkip)
        .limit(num)
    )
    docs = await wines.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content=[])
        response.status_code = 200
        return response
    for doc in docs:
        doc["url"] = "/wines/" + str(doc["wineID"])
    return docs


@router.get("/{userID}/liked-winelists")
async def get_listof_user_liked_winelist(
    request: Request, userID: int = -1, num: int = 20, page: int = 1
):
    # TODO 204 -> 200 []
    toSkip = num * (page - 1)
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    likedWinelists = user["likedWinelists"]
    winelists = (
        request.app.mongodb["winelist"]
        .find(
            {"winelistID": {"$in": likedWinelists}, "isDeleted": False},
            {
                "_id": 0,
                "winelistID": 1,
                "name": 1,
                "thumbnailImage": 1,
                "createdAt": 1,
                "lastUpdatedAt": 1,
            },
        )
        .skip(toSkip)
        .limit(num)
    )
    docs = await winelists.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content=[])
        response.status_code = 200
        return response
    for doc in docs:
        doc["url"] = "/winelists/" + str(doc["winelistID"])
    return docs


@router.post("/{userID}/like-review")
async def like_review(request: Request, userID: int = -1, reviewID: int = -1):
    # TODO DOC UPDATE
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    review = await request.app.mongodb["review"].find_one(
        {"reviewID": reviewID}, {"_id": 0}
    )
    if review == None:
        response = JSONResponse(content="No such review exists")
        response.status_code = 404
        return response
    if reviewID not in review["likedBy"]:
        review = await request.app.mongodb["review"].find_one_and_update(
            {"reviewID": reviewID},
            {
                "$push": {"likedBy": userID},
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
        review = await request.app.mongodb["review"].find_one_and_update(
            {"reviewID": reviewID},
            {
                "$pull": {"likedBy": userID},
                "$set": {
                    "lastUpdatedAt": datetime.now()
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S"),
                },
            },
            {"_id": 0},
            return_document=ReturnDocument.AFTER,
        )
    if review == None:
        response = JSONResponse(content="An error occurred while updating review")
        response.status_code = 404
        return response
    return {
        "reviewID": review["reviewID"],
        "likedUser": userID,
        "lastUpdatedAt": review["lastUpdatedAt"],
    }


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
    tags: list[str] = Query([]),
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
            targetUserAppend = await request.app.mongodb["user"].find_one_and_update(
                {"userID": targetUserID},
                {
                    "$pull": {"followers": userID},
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
            targetUserAppend = await request.app.mongodb["user"].find_one_and_update(
                {"userID": targetUserID},
                {
                    "$push": {"followers": userID},
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
            targetUserAppend = await request.app.mongodb["user"].find_one_and_update(
                {"userID": targetUserID},
                {
                    "$pull": {"following": userID},
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
            response = JSONResponse(content="target user is not in the follower list")
            response.status_code = 404
            return response
        # else:
        #     user = await request.app.mongodb["user"].find_one_and_update(
        #         {"userID": userID},
        #         {
        #             "$push": {"followers": targetUserID},
        #             "$set": {
        #                 "lastUpdatedAt": datetime.now()
        #                 .astimezone()
        #                 .strftime("%Y-%m-%d %H:%M:%S"),
        #             },
        #         },
        #         {"_id": 0},
        #         return_document=ReturnDocument.AFTER,
        #     )
        #     targetUserAppend = await request.app.mongodb["user"].find_one_and_update(
        #         {"userID": targetUserID},
        #         {
        #             "$push": {"following": userID},
        #             "$set": {
        #                 "lastUpdatedAt": datetime.now()
        #                 .astimezone()
        #                 .strftime("%Y-%m-%d %H:%M:%S"),
        #             },
        #         },
        #         {"_id": 0},
        #         return_document=ReturnDocument.AFTER,
        #     )
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


@router.post("/user-population")
async def user_population(request: Request, num: int = 50):
    for i in range(num):
        newUserID = await request.app.mongodb["auto_incrementer"].find_one_and_update(
            {"_id": "user"}, {"$inc": {"index": 1}}, {"index": 1}
        )
        userJson = {
            "userID": newUserID["index"],
            "username": "testUser" + str(newUserID["index"]),
            "email": "testEmail" + str(newUserID["index"]) + "@test.com",
            "profileImage": "https://oneego-image-storage.s3.ap-northeast-2.amazonaws.com/Archive/duck/duck_1.jpg",
            "phone": "",
            "gender": "M",
            "status": 0,
            "likedWines": [],
            "likedWinelists": [],
            "isDeleted": False,
            "createdAt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "lastUpdatedAt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": [],
            "followings": [],
            "followers": [],
        }
        newUser = await request.app.mongodb["user"].insert_one(userJson)
        if newUser == None:
            raise HTTPException(400)
        time.sleep(1)
        await review_population(request, userID=newUserID["index"])
        print("userID", newUserID["index"], "has been added to database.")


@router.post("/review-population")
async def review_population(request: Request, userID: int = -1, num: int = 20):

    for i in range(num):
        newReviewID = await request.app.mongodb["auto_incrementer"].find_one_and_update(
            {"_id": "review"}, {"$inc": {"index": 1}}, {"index": 1}
        )
        reviewJson = {
            "wineID": random.randint(0, 3000),
            "reviewID": newReviewID["index"],
            "userID": userID,
            "username": "testUser" + str(userID),
            "rating": random.randint(1, 5),
            "content": "This is good wine by user" + str(userID),
            "isDeleted": False,
            "createdAt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "lastUpdatedAt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": [],
            "comments": [],
            "likedBy": [],
            "userStatus": 0,
        }
        while True:
            checkReview = await request.app.mongodb["review"].find_one(
                {"wineID": reviewJson["wineID"], "userID": userID}, {"_id": 0}
            )
            if checkReview:
                reviewJson["wineID"] = random.randin(0, 3000)
                break
        newReview = await request.app.mongodb["review"].insert_one(reviewJson)
        if newReview == None:
            raise HTTPException(400)
        # await comment_population(
        #     request=request, userID=userID, reviewID=newReviewID["index"]
        # )
        print("reviewID", newReviewID["index"], "has been added to database.")


@router.post("/comment-population")
async def comment_population(
    request: Request, userID: int = -1, reviewID: int = -1, num: int = 10
):
    number = random.randint(0, num)
    for i in range(number):
        newCommentID = await request.app.mongodb[
            "auto_incrementer"
        ].find_one_and_update({"_id": "comment"}, {"$inc": {"index": 1}}, {"index": 1})
        commentJson = {
            "commentID": newCommentID["index"],
            "userID": userID,
            "content": "Thank you for the helpful review" + str(userID),
            "createdAt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "lastUpdatedAt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "isDeleted": False,
        }
        appendComment = await request.app.mongodb["review"].find_one_and_update(
            {"reviewID": reviewID},
            {
                "$push": {"comments": commentJson},
            },
            {"_id": 0},
            return_document=ReturnDocument.AFTER,
        )
        if appendComment == None:
            raise HTTPException(400)
        print("commentID", newCommentID["index"], "has been added to database.")
