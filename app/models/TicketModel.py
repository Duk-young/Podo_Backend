from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
import datetime


class SupportTicketModel(BaseModel):
    userID: int = Field(...)
    adminID: int = Field(None)
    title: str = Field(...)
    userQuestion: str = Field(...)
    adminReponse: str = Field("")
    createdAt: datetime = Field(
        datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    lastUpdatedAt: datetime = Field(
        datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )


class VerificationTicketModel(BaseModel):
    userID: int = Field(...)
    adminID: int = Field(None)
    verificationImage: str = Field("")
    userExplanation: str = Field("")
    status: int = Field(0)
    adminFeedback: str = Field("")
    isDeleted: bool = Field(False)
    createdAt: datetime = Field(
        datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    lastUpdatedAt: datetime = Field(
        datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
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
