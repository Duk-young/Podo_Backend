from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
from datetime import datetime


class WineModel(BaseModel):
    tags: list[str] = Field([])
    name: str = Field(...)
    images: list[str] = Field([])
    lightness: float = Field(0)  # 변경
    smoothness: float = Field(0)  # 변경
    sweetness: float = Field(0)  # 변경
    softness: float = Field(0)  # 변경
    abv: float = Field(0)
    price: float = Field(0)
    region: str = Field("")
    closure: str = Field("")
    grapes: list[str] = Field([])  # 변경
    rating: int = Field(0)  # 변경
    winery: str = Field([])
    description: str = Field("")
    views: int = Field(0)
    likes: list[int] = Field([])
    isDeleted: bool = Field(False)
    createdAt: datetime = Field(
        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    )
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
