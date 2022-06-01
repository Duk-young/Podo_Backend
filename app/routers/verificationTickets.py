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
from ..models.TicketModel import VerificationTicketModel, VerificationTicketAnswerModel
from typing import List, Optional
from tempfile import TemporaryFile
from datetime import datetime

router = APIRouter(
    prefix="/verification-tickets",
    tags=["verification-tickets"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
        204: {"description": "No content found"},
    },
)


@router.get("/total")
async def get_total_verification_tickets(request: Request, userID: int = -1):
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    match = {}
    if user["status"] != 2:
        match["userID"] = userID
    tickets = request.app.mongodb["verificationTicket"].find(match, {"_id": 0})
    docs = await tickets.to_list(None)
    return {"totalVerificationTickets": len(docs)}


@router.get("")
async def get_verification_tickets(
    request: Request, userID: int = -1, status: int = -1, num: int = 10, page: int = 1
):
    toSkip = num * (page - 1)
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    verificationTickets = None
    ticketStatus = []
    if status == -1:
        ticketStatus = [0, 1, 2]
    else:
        ticketStatus.append(status)
    match = {"$match": {"status": {"$in": ticketStatus}}}
    if requester["status"] != 2:
        match["$match"]["userID"] = userID
    verificationTickets = request.app.mongodb["verificationTicket"].aggregate(
        [
            match,
            {
                "$lookup": {
                    "from": "user",
                    "localField": "userID",
                    "foreignField": "userID",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                                "username": 1,
                            }
                        }
                    ],
                    "as": "userInfo",
                }
            },
            {
                "$project": {
                    "_id": 0,
                }
            },
            {"$sort": {"_id": -1}},
            {"$skip": toSkip},
            {"$limit": num},
        ]
    )
    docs = await verificationTickets.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content=[])
        response.status_code = 200
        return response
    result = []
    for doc in docs:
        if len(doc["userInfo"]) != 0:
            doc["username"] = doc["userInfo"][0]["username"]
            doc.pop("userInfo")
            result.append(doc)
    return result


@router.post("")
async def post_verification_ticket(
    request: Request, ticketInfo: VerificationTicketModel = Body(...)
):
    json_ticketInfo = jsonable_encoder(ticketInfo)
    user = await request.app.mongodb["user"].find_one(
        {"userID": json_ticketInfo["userID"]}, {"_id": 0}
    )
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    newTicketID = await request.app.mongodb["auto_incrementer"].find_one_and_update(
        {"_id": "verificationTicket"}, {"$inc": {"index": 1}}, {"index": 1}
    )
    json_ticketInfo["ticketID"] = newTicketID["index"]
    newverificationTicket = await request.app.mongodb["verificationTicket"].insert_one(
        json_ticketInfo
    )

    if newverificationTicket == None:
        response = JSONResponse(content="An error occurred while creating a new ticket")
        response.status_code = 400
        return response
    response = JSONResponse(
        content={
            "ticketID": newTicketID["index"],
            "createdAt": json_ticketInfo["createdAt"],
        }
    )
    return response


@router.get("/{ticketID}")
async def get_verification_ticket(
    request: Request, userID: int = -1, ticketID: int = -1
):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    verificationTicket = await request.app.mongodb["verificationTicket"].find_one(
        {"ticketID": ticketID}, {"_id": 0}
    )
    if verificationTicket == None:
        response = JSONResponse(content="No such verification ticket exists")
        response.status_code = 404
        return response
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2 and verificationTicket["userID"] != userID:
        response = JSONResponse(content="User is not authorized for this action")
        response.status_code = 401
        return response
    return verificationTicket


@router.put("/answer")
async def answer_verification_tickets(
    request: Request,
    ticketInfo: VerificationTicketAnswerModel = Body(...),
):
    json_ticketInfo = jsonable_encoder(ticketInfo)
    admin = await request.app.mongodb["user"].find_one(
        {"userID": json_ticketInfo["adminID"]}, {"_id": 0}
    )
    if admin == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if admin["status"] != 2:
        response = JSONResponse(content="The user is not admin")
        response.status_code = 401
        return response
    verificationTicket = await request.app.mongodb[
        "verificationTicket"
    ].find_one_and_update(
        {"ticketID": json_ticketInfo["ticketID"]},
        {
            "$set": {
                "adminID": json_ticketInfo["adminID"],
                "adminFeedback": json_ticketInfo["adminFeedback"],
                "status": json_ticketInfo["status"],
                "lastUpdatedAt": json_ticketInfo["lastUpdatedAt"],
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if verificationTicket == None:
        response = JSONResponse(content="An error occurred while updating ticket")
        response.status_code = 404
        return response
    return {
        "ticketID": json_ticketInfo["ticketID"],
        "lastUpdatedAt": verificationTicket["lastUpdatedAt"],
    }


@router.put("/{tickeID}")
async def update_verification_tickets(
    request: Request,
    ticketID: int = -1,
    ticketInfo: VerificationTicketModel = Body(...),
):
    json_ticketInfo = jsonable_encoder(ticketInfo)
    user = await request.app.mongodb["user"].find_one(
        {"userID": json_ticketInfo["userID"]}, {"_id": 0}
    )
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    verificationTicket = await request.app.mongodb[
        "verificationTicket"
    ].find_one_and_update(
        {"ticketID": ticketID, "userID": json_ticketInfo["userID"]},
        {
            "$set": {
                "verificationImage": json_ticketInfo["verificationImage"],
                "userExplanation": json_ticketInfo["userExplanation"],
                "lastUpdatedAt": datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if verificationTicket == None:
        response = JSONResponse(content="An error occurred while updating ticket")
        response.status_code = 404
        return response
    return {
        "ticketID": ticketID,
        "lastUpdatedAt": verificationTicket["lastUpdatedAt"],
    }
