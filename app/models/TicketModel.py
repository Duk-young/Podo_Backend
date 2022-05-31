from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
from datetime import datetime


class SupportTicketModel(BaseModel):
    userID: int = Field(...)
    adminID: int = Field(None)
    title: str = Field(...)
    status: int = Field(2)
    userQuestion: str = Field(...)
    adminResponse: str = Field("")
    createdAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    lastUpdatedAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )


class SupportTicketAnswerModel(BaseModel):
    ticketID: int = Field(...)
    adminID: int = Field(...)
    adminResponse: str = Field("")
    lastUpdatedAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )


class VerificationTicketModel(BaseModel):
    userID: int = Field(...)
    adminID: int = Field(None)
    verificationImage: str = Field("")
    userExplanation: str = Field("")
    status: int = Field(2)
    adminFeedback: str = Field("")
    isDeleted: bool = Field(False)
    createdAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    lastUpdatedAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )


class VerificationTicketAnswerModel(BaseModel):
    ticketID: int = Field(...)
    adminID: int = Field(...)
    status: int = Field(...)
    adminFeedback: str = Field("")
    lastUpdatedAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "desktopURL": "www.naver.com/imageDesktop",
                "mobileURL": "www.naver.com/imageMobile",
                "link": "www.naver.com",
            }
        }
