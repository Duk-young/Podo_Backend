from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError, validator
from datetime import datetime


class TagsModel(BaseModel):
    names: list[str] = Field([])

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "desktopURL": "www.naver.com/imageDesktop",
                "mobileURL": "www.naver.com/imageMobile",
                "link": "www.naver.com",
            }
        }
