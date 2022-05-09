from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
from datetime import datetime


class CommentModel(BaseModel):
    userID: int = Field(...)
    content: str = Field(...)
    isDeleted: bool = Field(False)
    createdAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    lastUpdatedAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )


class ReviewModel(BaseModel):
    # wineID: int = Field(...)
    userID: int = Field(...)
    content: str = Field("")
    rating: float = Field(0)
    isDeleted: bool = Field(False)
    createdAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    lastUpdatedAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    tags: list[str] = Field([])
    comments: list[CommentModel] = Field([])

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "desktopURL": "www.naver.com/imageDesktop",
                "mobileURL": "www.naver.com/imageMobile",
                "link": "www.naver.com",
            }
        }
