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
from ..models.TicketModel import VerificationTicketModel
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
    if user["status"] != 2:
        response = JSONResponse(content="user is not the admin")
        response.status_code = 401
        return response
    tickets = request.app.mongodb["verificationTicket"].find({}, {"_id": 0})
    docs = await tickets.to_list(None)
    return {"totalVerificationTickets": len(docs)}


@router.get("")
async def get_verification_tickets(
    request: Request, userID: int = -1, status: int = 1, num: int = 10, page: int = 1
):  # TODO DOC 수정 필요
    toSkip = num * (page - 1)
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    if requester == None:
        response = JSONResponse(content="No such user exists")
        response.status_code = 404
        return response
    # if requester["status"] != 2:
    #     response = JSONResponse(content="User is not authorized for this action")
    #     response.status_code = 401
    #     return response
    verificationTickets = None
    if requester["status"] == 2:
        verificationTickets = (
            request.app.mongodb["verificationTicket"]
            .find({}, {"_id": 0})
            .sort("_id", -1)
            .skip(toSkip)
            .limit(num)
        )
    else:
        verificationTickets = (
            request.app.mongodb["verificationTicket"]
            .find({"userID": userID}, {"_id": 0})
            .sort("_id", -1)
            .skip(toSkip)
            .limit(num)
        )
    docs = await verificationTickets.to_list(None)
    if len(docs) == 0:
        response = JSONResponse(content="No verification tickets exists in DB")
        response.status_code = 204
        return response
    return docs


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
async def get_verification_tickets(
    request: Request, userID: int = -1, ticketID: int = -1
):
    requester = await request.app.mongodb["user"].find_one(
        {"userID": userID}, {"_id": 0}
    )
    verificationTicket = request.app.mongodb["verificationTicket"].find(
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


@router.put("/{tickeID}/answer")
async def update_verification_tickets(
    request: Request,
    ticketID: int = -1,
    ticketInfo: VerificationTicketModel = Body(...),
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
        {"ticketID": ticketID, "userID": json_ticketInfo["userID"]},
        {
            "$set": {
                "adminID": json_ticketInfo["adminID"],
                "adminFeedback": json_ticketInfo["adminFeedback"],
                "status": json_ticketInfo["status"],
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
