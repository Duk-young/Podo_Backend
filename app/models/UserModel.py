from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
from datetime import datetime


class UserModel(BaseModel):
    username: str = Field(...)
    email: str = Field(...)
    profileImage: str = Field("")
    phone: str = Field("")
    gender: str = Field("")
    status: str = Field(0)
    likedWines: list[str] = Field([])
    likedWinelists: list[str] = Field([])
    isDeleted: bool = Field(False)
    createdAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    lastUpdatedAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    tags: list[str] = Field([])
    followings: list[str] = Field([])
    followers: list[str] = Field([])

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "desktopURL": "www.naver.com/imageDesktop",
                "mobileURL": "www.naver.com/imageMobile",
                "link": "www.naver.com",
            }
        }
