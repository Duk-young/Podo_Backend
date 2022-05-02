from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
from datetime import datetime


class CarouselSlide(BaseModel):
    image: str = Field(...)
    isHidden: bool = Field(False)


class CarouselModel(BaseModel):
    CarouselSlides: list[CarouselSlide] = Field(...)  # 변경

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "desktopURL": "www.naver.com/imageDesktop",
                "mobileURL": "www.naver.com/imageMobile",
                "link": "www.naver.com",
            }
        }
