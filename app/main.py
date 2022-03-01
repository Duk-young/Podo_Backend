import os
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import boto3

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
        DB_ADDRESS + "?ssl=true&ssl_cert_reqs=CERT_NONE"
    )


@app.get("/")
async def root():
    return {"message": "Hello World"}
