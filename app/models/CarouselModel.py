from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
import datetime


class CarouselSlides(BaseModel):
    image: str = Field(...)
    isHidden: bool = Field(False)


class CarouselModel(BaseModel):
    CarouselSlide: list[CarouselSlides] = Field(...)  # Change

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "desktopURL": "www.naver.com/imageDesktop",
                "mobileURL": "www.naver.com/imageMobile",
                "link": "www.naver.com",
            }
        }
