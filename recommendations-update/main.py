import os
import pymongo
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import pandas as pd
import s3fs
import requests

load_dotenv()

DB_ADDRESS = os.getenv("DB_ADDRESS")
DB_NAME = os.getenv("DB_NAME")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
RECOMMENDATIONS_UPDATE_URL = os.getenv("RECOMMENDATIONS_UPDATE_URL")
sched = BlockingScheduler(timezone="Asia/Seoul")
folderName = "/recommendations/"
# 매일 00:05 분에 백업 실행
# @sched.scheduled_job('cron', day_of_week='0-6',hour='0',minute='5')
def backup_db():
    client = pymongo.MongoClient(DB_ADDRESS)
    database = client[str(DB_NAME)]
    filenames = ["wines.csv", "reviews.csv"]
    wines = database["wine"]
    wineData = wines.find(
        {},
        {
            "_id": 0,
            "name": 1,
            "wineID": 1,
            "tags": 1,
            "grape": 1,
            "lightness": 1,
            "smoothness": 1,
            "sweetness": 1,
            "softness": 1,
            "abv": 1,
        },
    )
    wineDocs = list(wineData)
    reviews = database["review"]
    reviewData = reviews.find({}, {"_id": 0, "wineID": 1, "userID": 1, "rating": 1})
    reviewDocs = list(reviewData)

    ## wineData
    wineNames = [data["name"] for data in wineDocs]
    wineIDs = [data["wineID"] for data in wineDocs]
    wineTags = [data["tags"] for data in wineDocs]
    wineGrapes = [data["grape"] for data in wineDocs]
    wineLightness = [data["lightness"] for data in wineDocs]
    wineSmoothness = [data["smoothness"] for data in wineDocs]
    wineSweetness = [data["sweetness"] for data in wineDocs]
    wineSoftness = [data["softness"] for data in wineDocs]
    wineAbv = [data["abv"] for data in wineDocs]
    # field names
    df = {
        "wineID": wineIDs,
        "name": wineNames,
        "tags": wineTags,
        "grape": wineGrapes,
        "lightness": wineLightness,
        "smoothness": wineSmoothness,
        "sweetness": wineSweetness,
        "softness": wineSoftness,
        "abv": wineAbv,
    }
    wineDF = pd.DataFrame(df)

    ## reviewData
    wineIDs = [data["wineID"] for data in reviewDocs]
    userIDs = [data["userID"] for data in reviewDocs]
    ratings = [data["rating"] for data in reviewDocs]
    # field names
    df = {"wineID": wineIDs, "userID": userIDs, "rating": ratings}
    reviewDF = pd.DataFrame(df)

    fs = s3fs.S3FileSystem(key=AWS_ACCESS_KEY, secret=AWS_SECRET_KEY)
    for filename in filenames:
        bytes_to_write = None
        if filename == "wines.csv":
            bytes_to_write = wineDF.to_csv(None).encode()
        else:
            bytes_to_write = reviewDF.to_csv(None).encode()
        with fs.open(AWS_BUCKET_NAME + folderName + filename, "wb") as f:
            f.write(bytes_to_write)
        print(filename, "has been successfully uploaded.")
    response = requests.get(RECOMMENDATIONS_UPDATE_URL)
    print(response.status_code, response.text)


def main():
    now = datetime.now()
    print("Backup scheduler up at:", now)
    backup_db()


main()
