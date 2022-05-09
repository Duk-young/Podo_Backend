import json
from xml.etree.ElementTree import Comment
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
from ..models.WineModel import WineModel
from ..models.ReviewModel import ReviewModel, CommentModel
from datetime import datetime

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
    tags: list[str] = Query([]),
):
    # TODO sorting 방식
    toSkip = num * (page - 1)
    wines = None
    print(tags)
    if len(tags) == 0:
        # wines = (
        #     request.app.mongodb["wine"]
        #     .find(
        #         {
        #             "$and": [
        #                 {"price": {"$gte": minPrice}},
        #                 {"price": {"$lte": maxPrice}},
        #                 {"rating": {"$gte": minRating}},
        #                 {"isDeleted": False},
        #             ],
        #             "name": {"$regex": keyword, "$options": "i"},
        #         },
        #         {"_id": 0},
        #     )
        #     .sort("_id", -1)
        #     .skip(toSkip)
        #     .limit(num)
        # )
        wines = request.app.mongodb["wine"].aggregate(
            [
                {"$sort": {"_id": -1}},
                {
                    "$match": {
                        "name": {"$regex": keyword, "$options": "i"},
                        "price": {"$gte": minPrice},
                        "price": {"$lte": maxPrice},
                        "rating": {"$gte": minRating},
                        "isDeleted": False,
                    }
                },
                {"$skip": toSkip},
                {"$limit": num},
                {  # lookup for reviews
                    "$lookup": {
                        "from": "review",
                        "localField": "wineID",
                        "foreignField": "wineID",
                        "pipeline": [
                            {
                                "$group": {
                                    "_id": None,
                                    "totalReviews": {"$sum": 1},
                                },
                            },
                            {
                                "$project": {
                                    "_id": 0,
                                },
                            },
                        ],
                        "as": "reviews",
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                    }
                },
            ]
        )
    else:
        wines = request.app.mongodb["wine"].aggregate(
            [
                {"$sort": {"_id": -1}},
                {
                    "$match": {
                        "name": {"$regex": keyword, "$options": "i"},
                        "price": {"$gte": minPrice},
                        "price": {"$lte": maxPrice},
                        "rating": {"$gte": minRating},
                        "isDeleted": False,
                        "tags": {"$in": tags},
                    }
                },
                {"$skip": toSkip},
                {"$limit": num},
                {  # lookup for reviews
                    "$lookup": {
                        "from": "review",
                        "localField": "wineID",
                        "foreignField": "wineID",
                        "pipeline": [
                            {
                                "$group": {
                                    "_id": None,
                                    "totalReviews": {"$sum": 1},
                                },
                            },
                            {
                                "$project": {
                                    "_id": 0,
                                },
                            },
                        ],
                        "as": "reviews",
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                    }
                },
            ]
        )
    docs = await wines.to_list(None)
    for doc in docs:
        if len(doc["reviews"]) > 0:
            doc["totalReviews"] = doc["reviews"][0]["totalReviews"]
        else:
            doc["totalReviews"] = 0
        doc.pop("reviews")
    if len(docs) == 0:
        response = JSONResponse(content="No wines exists")
        response.status_code = 204
        return response
    return docs


@router.get("/total")
async def total_wines(request: Request):
    wines = request.app.mongodb["wine"].find({}, {"_id": 0})
    docs = await wines.to_list(None)
    return {"totalWines": len(docs)}


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
    json_wineInfo["wineID"] = newWineID["index"]
    newWine = await request.app.mongodb["wine"].insert_one(json_wineInfo)
    if newWine == None:
        response = JSONResponse(
            content="An error occurred while creating new wine object"
        )
        response.status_code = 400
        return response
    else:
        response = JSONResponse(
            content={
                "wineID": newWineID["index"],
                "createdAt": json_wineInfo["createdAt"],
            }
        )
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
        {"wineID": wineID},
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
    if wine != None:
        return {
            "wineID": wine["wineID"],
            "isDeleted": wine["isDeleted"],
            "lastUpdatedAt": wine["lastUpdatedAt"],
        }
    return "Failed to restore wine."


@router.get("/{wineID}")
async def get_wine(request: Request, wineID: int, userID: int = -1):
    # DOCS UPDATE 필요
    wine = await request.app.mongodb["wine"].find_one_and_update(
        {"wineID": wineID},
        {"$inc": {"views": 1}},
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if wine == None:
        response = JSONResponse(content="No such wine exists")
        response.status_code = 404
        return response
    wine = request.app.mongodb["wine"].aggregate(
        [
            {
                "$match": {
                    "isDeleted": False,
                    "wineID": wineID,
                },
            },
            {  # lookup for reviews
                "$lookup": {
                    "from": "review",
                    "localField": "wineID",
                    "foreignField": "wineID",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                            }
                        }
                    ],
                    "as": "reviews",
                }
            },
            {
                "$project": {
                    "_id": 0,
                }
            },
        ]
    )
    wine = await wine.to_list(None)
    wine = wine[0]
    for review in wine["reviews"]:
        if userID in review["likedBy"]:
            review["userLiked"] = True
        else:
            review["userLiked"] = False
        review.pop("likedBy")
    return wine


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
        return_document=ReturnDocument.AFTER,
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
        {"wineID": wineID},
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
    if wine != None:
        return {
            "wineID": wine["wineID"],
            "isDeleted": wine["isDeleted"],
            "lastUpdatedAt": wine["lastUpdatedAt"],
        }
    return "Failed to restore wine."


########################################################
########################################################
########################################################
###########   Review API beyond this line   ############
########################################################
########################################################
########################################################


@router.get("/{wineID}/reviews/total")
async def get_total_wine_reviews(request: Request, wineID: int = -1):
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    reviews = request.app.mongodb["review"].find({"wineID": wineID}, {"_id": 0})
    docs = await reviews.to_list(None)

    if len(docs) == 0:
        response = JSONResponse(content="No reviews exists")
        response.status_code = 204
        return response
    return {"wineID": wineID, "totalReviews": len(docs)}


@router.get("/{wineID}/reviews/{reviewID}/comments/total")
async def get_total_wine_review_comments(
    request: Request, wineID: int = -1, reviewID: int = -1
):
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    review = await request.app.mongodb["review"].find_one(
        {"wineID": wineID, "reviewID": reviewID}, {"_id": 0}
    )

    if review == None:
        response = JSONResponse(content="No review exists")
        response.status_code = 204
        return response

    return {
        "wineID": wineID,
        "reviewID": reviewID,
        "totalComments": len(review["comments"]),
    }


@router.get("/{wineID}/reviews")
async def get_wine_reviews(
    request: Request, wineID: int = -1, num: int = 20, sort: int = 1, page: int = 1
):
    toSkip = num * (page - 1)
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    reviews = (
        request.app.mongodb["review"]
        .find({"wineID": wineID}, {"_id": 0})
        .sort("_id", -1)
        .skip(toSkip)
        .limit(num)
    )
    docs = await reviews.to_list(None)

    if len(docs) == 0:
        response = JSONResponse(content="No reviews exists")
        response.status_code = 204
        return response
    return docs


@router.get("/{wineID}/reviews/{reviewID}/comments")
async def get_wine_review_comments(
    request: Request,
    wineID: int = -1,
    reviewID: int = -1,
    num: int = 20,
    sort: int = 1,
    page: int = 1,
):
    toSkip = num * (page - 1)
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    review = await request.app.mongodb["review"].find_one(
        {"wineID": wineID, "reviewID": reviewID}, {"_id": 0}
    )

    if review == 0:
        response = JSONResponse(content="No reviews exists")
        response.status_code = 204
        return response
    return review["comments"][toSkip : toSkip + num]


@router.post("/{wineID}/reviews")
async def post_wine_reviews(
    request: Request, wineID: int = -1, reviewInfo: ReviewModel = Body(...)
):
    json_reviewInfo = jsonable_encoder(reviewInfo)
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    user = await request.app.mongodb["user"].find_one(
        {"userID": json_reviewInfo["userID"]}, {"_id": 0}
    )
    if user == None:
        response = JSONResponse(content="userID is invalid. No such user exists in DB")
        response.status_code = 404
        return response
    newReviewID = await request.app.mongodb["auto_incrementer"].find_one_and_update(
        {"_id": "review"}, {"$inc": {"index": 1}}, {"index": 1}
    )
    json_reviewInfo["wineID"] = wineID
    json_reviewInfo["reviewID"] = newReviewID["index"]
    newReview = await request.app.mongodb["review"].insert_one(json_reviewInfo)
    if newReview == None:
        response = JSONResponse(
            content="An error occurred while creating new review object"
        )
        response.status_code = 400
        return response
    else:
        response = JSONResponse(
            content={
                "reviewID": newReviewID["index"],
                "createdAt": json_reviewInfo["createdAt"],
            }
        )
    # update rating
    await update_rating(request, wineID=wineID)
    response.status_code = 201
    return response


@router.post("/{wineID}/reviews/{reviewID}/comments")
async def post_wine_reviews(
    request: Request,
    wineID: int = -1,
    reviewID: int = -1,
    commentInfo: CommentModel = Body(...),
):
    json_commentInfo = jsonable_encoder(commentInfo)
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    review = await request.app.mongodb["review"].find_one(
        {"reviewID": reviewID}, {"_id": 0}
    )
    if review == None:
        response = JSONResponse(
            content="reviewID is invalid. No such review exists in DB"
        )
        response.status_code = 404
        return response
    user = await request.app.mongodb["user"].find_one(
        {"userID": json_commentInfo["userID"]}, {"_id": 0}
    )
    if user == None:
        response = JSONResponse(content="userID is invalid. No such user exists in DB")
        response.status_code = 404
        return response
    newCommentID = await request.app.mongodb["auto_incrementer"].find_one_and_update(
        {"_id": "comment"}, {"$inc": {"index": 1}}, {"index": 1}
    )
    json_commentInfo["commentID"] = newCommentID["index"]
    appendComment = await request.app.mongodb["review"].find_one_and_update(
        {"reviewID": reviewID},
        {
            "$push": {"comments": json_commentInfo},
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )

    if appendComment == None:
        response = JSONResponse(
            content="An error occurred while creating new review object"
        )
        response.status_code = 400
        return response
    else:
        response = JSONResponse(
            content={
                "commentID": newCommentID["index"],
                "createdAt": json_commentInfo["createdAt"],
            }
        )
        response.status_code = 201
        return response


@router.put("/{wineID}/reviews/{reviewID}")
async def update_review(
    request: Request,
    wineID: int = -1,
    reviewID: int = -1,
    reviewInfo: ReviewModel = Body(...),
):
    json_reviewInfo = jsonable_encoder(reviewInfo)
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    user = await request.app.mongodb["user"].find_one(
        {"userID": json_reviewInfo["userID"]}, {"_id": 0}
    )
    if user == None:
        response = JSONResponse(content="userID is invalid. No such user exists in DB")
        response.status_code = 404
        return response
    updatedReview = await request.app.mongodb["review"].find_one_and_update(
        {"reviewID": reviewID, "userID": json_reviewInfo["userID"]},
        {
            "$set": {
                "content": json_reviewInfo["content"],
                "rating": json_reviewInfo["rating"],
                "tags": json_reviewInfo["tags"],
                "lastUpdatedAt": datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if updatedReview == None:
        response = JSONResponse(
            content="An error occurred while updating new review object"
        )
        response.status_code = 400
        return response
    else:
        await update_rating(request, wineID=wineID)
        response = JSONResponse(
            content={
                "reviewID": updatedReview["index"],
                "lastUpdatedAt": updatedReview["lastUpdatedAt"],
            }
        )
        return response


@router.put("/{wineID}/reviews/{reviewID}/comments/{commentID}")
async def update_review_comment(
    request: Request,
    wineID: int = -1,
    reviewID: int = -1,
    commentID: int = -1,
    commentInfo: CommentModel = Body(...),
):
    json_commentInfo = jsonable_encoder(commentInfo)
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    user = await request.app.mongodb["user"].find_one(
        {"userID": json_commentInfo["userID"]}, {"_id": 0}
    )
    if user == None:
        response = JSONResponse(content="userID is invalid. No such user exists in DB")
        response.status_code = 404
        return response
    updatedComment = await request.app.mongodb["review"].find_one_and_update(
        {
            "reviewID": reviewID,
            "comments": {
                "$elemMatch": {
                    "userID": json_commentInfo["userID"],
                    "commentID": json_commentInfo["commentID"],
                }
            },
        },
        {
            "$set": {
                "comments": {
                    "content": json_commentInfo["content"],
                    "lastUpdatedAt": datetime.now()
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S"),
                }
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if updatedComment == None:
        response = JSONResponse(
            content="An error occurred while updating new review object"
        )
        response.status_code = 400
        return response
    else:
        response = JSONResponse(
            content={
                "commentID": updatedComment["index"],
                "lastUpdatedAt": updatedComment["lastUpdatedAt"],
            }
        )
        return response


@router.delete("/{wineID}/reviews/{reviewID}")
async def delete_wine_reviews(
    request: Request, wineID: int = -1, reviewID: int = -1, userID: int = -1
):
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="userID is invalid. No such user exists in DB")
        response.status_code = 404
        return response
    review = await request.app.mongodb["review"].find_one(
        {"reviewID": reviewID, "userID": userID}, {"_id": 0}
    )
    if review == None:
        response = JSONResponse(
            content="reviewID is invalid. No such review exists in DB"
        )
        response.status_code = 404
        return response
    deleteReview = await request.app.mongodb["review"].find_one_and_update(
        {"reviewID": reviewID, "userID": userID},
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
    if deleteReview == None:
        response = JSONResponse(
            content="An error occurred while creating new review object"
        )
        response.status_code = 400
        return response
    else:
        await update_rating(request, wineID=wineID)
        response = JSONResponse(
            content={
                "reviewID": deleteReview["reviewID"],
                "isDeleted": deleteReview["isDeleted"],
                "lastUpdatedAt": deleteReview["lastUpdatedAt"],
            }
        )
        return response


@router.delete("/{wineID}/reviews/{reviewID}/comments/{commentID}")
async def delete_wine_review_comment(
    request: Request,
    wineID: int = -1,
    reviewID: int = -1,
    commentID: int = -1,
    userID: int = -1,
):
    wine = await request.app.mongodb["wine"].find_one({"wineID": wineID}, {"_id": 0})
    if wine == None:
        response = JSONResponse(content="WineID is invalid. No such wine exists in DB")
        response.status_code = 404
        return response
    review = await request.app.mongodb["review"].find_one(
        {"reviewID": reviewID}, {"_id": 0}
    )
    if review == None:
        response = JSONResponse(
            content="reviewID is invalid. No such review exists in DB"
        )
        response.status_code = 404
        return response
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="userID is invalid. No such user exists in DB")
        response.status_code = 404
        return response

    deletedComment = await request.app.mongodb["review"].find_one_and_update(
        {
            "reviewID": reviewID,
            "comments": {
                "$elemMatch": {
                    "userID": userID,
                    "commentID": commentID,
                }
            },
        },
        {
            "$set": {
                "comments": {
                    "isDeleted": True,
                    "lastUpdatedAt": datetime.now()
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S"),
                }
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )

    if deletedComment == None:
        response = JSONResponse(
            content="An error occurred while creating new review object"
        )
        response.status_code = 400
        return response
    else:
        response = JSONResponse(
            content={
                "commentID": commentID,
                "isDeleted": deletedComment["isDeleted"],
                "lastUpdatedAt": deletedComment["lastUpdatedAt"],
            }
        )
        return response


async def update_rating(request: Request, wineID: int = -1):
    reviews = request.app.mongodb["review"].aggregate(
        [
            {
                "$match": {
                    "wineID": wineID,
                    "isDeleted": False,
                }
            },
            {
                "$group": {
                    "_id": None,
                    "rating": {"$sum": "$rating"},
                    "totalReviews": {"$sum": 1},
                },
            },
        ]
    )
    reviews = await reviews.to_list(None)
    reviews = reviews[0]
    totalRating = float(
        "{:.2f}".format(float(reviews["rating"]) / int(reviews["totalReviews"]))
    )
    wine = await request.app.mongodb["wine"].find_one_and_update(
        {"wineID": wineID},
        {"$set": {"rating": totalRating}},
        {"_id": 0},
    )
    if wine == None:
        response = JSONResponse(content="An error occured during the update")
        response.status_code = 400
        return response
    return
