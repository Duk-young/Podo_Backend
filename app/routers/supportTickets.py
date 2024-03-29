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
from ..models.TicketModel import SupportTicketModel, SupportTicketAnswerModel
from typing import List, Optional
from tempfile import TemporaryFile
from datetime import datetime

router = APIRouter(
    prefix="/support-tickets",
    tags=["support-tickets"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
        204: {"description": "No content found"},
    },
)


@router.get("/total")
async def get_total_support_tickets(request: Request, userID: int = -1):
    user = await request.app.mongodb["user"].find_one({"userID": userID}, {"_id": 0})
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    match = {}
    if user["status"] != 2:
        match["userID"] = userID
    tickets = request.app.mongodb["supportTicket"].find(match, {"_id": 0})
    docs = await tickets.to_list(None)
    return {"totalSupportTickets": len(docs)}


@router.get("")
async def get_support_tickets(
    request: Request, userID: int = -1, status: int = 0, num: int = 10, page: int = 1
):
    toSkip = num * (page - 1)
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    ticketStatus = []
    if status == 0:
        ticketStatus.append(1)
        ticketStatus.append(2)
    else:
        ticketStatus.append(status)
    match = {"$match": {"status": {"$in": ticketStatus}}}
    if requester["status"] != 2:
        match["$match"]["userID"] = userID
    supportTickets = request.app.mongodb["supportTicket"].aggregate(
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
    docs = await supportTickets.to_list(None)
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
    if len(docs) == 0:
        response = JSONResponse(content="No support tickets exists in DB")
        response.status_code = 204
        return response
    return result


@router.post("")
async def post_support_ticket(
    request: Request, ticketInfo: SupportTicketModel = Body(...)
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
        {"_id": "supportTicket"}, {"$inc": {"index": 1}}, {"index": 1}
    )
    json_ticketInfo["ticketID"] = newTicketID["index"]
    newSupportTicket = await request.app.mongodb["supportTicket"].insert_one(
        json_ticketInfo
    )

    if newSupportTicket == None:
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
async def get_support_ticket(request: Request, userID: int = -1, ticketID: int = -1):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    supportTicket = await request.app.mongodb["supportTicket"].find_one(
        {"ticketID": ticketID}, {"_id": 0}
    )
    if supportTicket == None:
        response = JSONResponse(content="No such support ticket exists")
        response.status_code = 404
        return response
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    if requester["status"] != 2 and supportTicket["userID"] != userID:
        response = JSONResponse(content="User is not authorized for this action")
        response.status_code = 401
        return response
    return supportTicket


@router.put("/answer")
async def answer_support_tickets(
    request: Request,
    ticketID: int = -1,
    ticketInfo: SupportTicketAnswerModel = Body(...),
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
    supportTicket = await request.app.mongodb["supportTicket"].find_one_and_update(
        {"ticketID": ticketID},
        {
            "$set": {
                "adminID": json_ticketInfo["adminID"],
                "adminResponse": json_ticketInfo["adminResponse"],
                "lastUpdatedAt": json_ticketInfo["lastUpdatedAt"],
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if supportTicket == None:
        response = JSONResponse(content="An error occurred while updating ticket")
        response.status_code = 404
        return response
    return {
        "ticketID": ticketID,
        "lastUpdatedAt": supportTicket["lastUpdatedAt"],
    }


@router.put("/{tickeID}")
async def update_support_tickets(
    request: Request, ticketID: int = -1, ticketInfo: SupportTicketModel = Body(...)
):
    json_ticketInfo = jsonable_encoder(ticketInfo)
    user = await request.app.mongodb["user"].find_one(
        {"userID": json_ticketInfo["userID"]}, {"_id": 0}
    )
    if user == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    supportTicket = await request.app.mongodb["supportTicket"].find_one_and_update(
        {"ticketID": ticketID, "userID": json_ticketInfo["userID"]},
        {
            "$set": {
                "title": json_ticketInfo["title"],
                "userQuestion": json_ticketInfo["userQuestion"],
                "lastUpdatedAt": datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
            }
        },
        {"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if supportTicket == None:
        response = JSONResponse(content="An error occurred while updating ticket")
        response.status_code = 404
        return response
    return {
        "ticketID": ticketID,
        "lastUpdatedAt": supportTicket["lastUpdatedAt"],
    }
