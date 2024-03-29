from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
from datetime import datetime


class SommelierPick(BaseModel):
    wineID: int = Field(...)
    sommelierComment: str = Field("")


class WinelistModel(BaseModel):
    userID: int = Field(...)
    title: str = Field("")
    thumbnailImage: str = Field("")
    tags: list[str] = Field([])
    content: str = Field("")
    wines: list[SommelierPick] = Field([])
    isDeleted: bool = Field(False)
    createdAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    lastUpdatedAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
    views: int = Field(0)
    likes: list[int] = Field([])

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "desktopURL": "www.naver.com/imageDesktop",
                "mobileURL": "www.naver.com/imageMobile",
                "link": "www.naver.com",
            }
        }
