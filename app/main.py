import os
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import boto3
from .routers import (
    verificationTickets,
    winelists,
    wines,
    users,
    supportTickets,
    s3upload,
)

# from .consts import origins
# from .routers import form, story, user, s3upload, transaction, store
import requests
import json

# dotenv initialize
load_dotenv()

# env var setups
DB_ADDRESS = os.getenv("DB_ADDRESS")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_IMAGE_SERVER_URL = os.getenv("AWS_IMAGE_SERVER_URL")
DB_ADDRESS = os.getenv("DB_ADDRESS")
RUNTIME_ENV = os.getenv("RUNTIME_ENV")
# initialize the app
app = FastAPI()


@app.on_event("startup")
def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(
        DB_ADDRESS + "" + "?ssl=true&ssl_cert_reqs=CERT_NONE"
    )
    app.mongodb = (
        app.mongodb_client["podo_prod"]
        if RUNTIME_ENV == "prod"
        else app.mongodb_client["podo_dev"]
    )
    app.imgurlstr = AWS_IMAGE_SERVER_URL
    app.s3 = boto3.resource(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
    )
    app.s3_bucket = app.s3.Bucket(AWS_BUCKET_NAME)


# include routers
app.include_router(wines.router)
app.include_router(winelists.router)
app.include_router(users.router)
app.include_router(supportTickets.router)
app.include_router(verificationTickets.router)
app.include_router(s3upload.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/dbtest")
async def db_test(request: Request):
    wine = await request.app.mongodb["wines"].find_one({"wineID": 0}, {"_id": 0})
    return wine


@app.get("/s3test")
async def s3_test(request: Request):
    print(AWS_IMAGE_SERVER_URL + "wines/")
    for dir in request.app.s3_bucket.objects.filter(Prefix="wines/"):  # 경로 존재 시 True 리턴
        return True
