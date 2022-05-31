from fastapi import (
    APIRouter,
    Body,
    Request,
    HTTPException,
    status,
    File,
    UploadFile,
    Form,
)
import os
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from httpcore import request
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# from sklearn.decomposition import TruncatedSVD
from scipy.sparse.linalg import svds
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

router = APIRouter(
    prefix="/wine-recommendations",
    tags=["wine-recommendations"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
    },
)
load_dotenv()
REVIEWS_DATA_URL = os.getenv("REVIEWS_DATA_URL")
WINES_DATA_URL = os.getenv("WINES_DATA_URL")
reviewData = pd.read_csv(REVIEWS_DATA_URL)
winesData = pd.read_csv(WINES_DATA_URL)
countVect = CountVectorizer(min_df=0, ngram_range=(1, 2))
tagsMat = countVect.fit_transform(winesData["tags"])
tagsSim = cosine_similarity(tagsMat, tagsMat)
tagsSimSortedInd = tagsSim.argsort()[:, ::-1]


# @router.get("/wine-based")
# async def wine_based_recommendations(request: Request, wineID: int = -1):
#     similar_wines = find_sim_wine(
#         winesData,
#         tagsSimSortedInd,
#         wineID,
#         10,
#     )
#     print(similar_wines)
#     return similar_wines[
#         [
#             "name",
#             "tags",
#             "grape",
#             "lightness",
#             "sweetness",
#             "smoothness",
#             "softness",
#             "abv",
#         ]
#     ]


@router.get("")
def get_wine_recommendations(
    request: Request, userID: int = -1, wineID: int = -1, num: int = 5
):
    ## For people who reviewed at least once
    similar_wines = find_sim_wine(
        winesData,
        tagsSimSortedInd,
        wineID,
        100,
    )
    indexes = list(similar_wines.index.values)
    filteredReviews = reviewData[reviewData["wineID"].isin(indexes)]
    userWineRatings = filteredReviews.pivot(
        index="userID", columns="wineID", values="rating"
    ).fillna(0)
    userIDs = {userID for userID in filteredReviews["userID"]}
    try:
        userID = list(userIDs).index(userID)
    except ValueError as e:
        print("userID", userID, "has no review")
        return list(similar_wines["wineID"])[:num]
    userWineRatings = pd.pivot_table(
        filteredReviews, index="userID", columns="wineID", values="rating"
    ).fillna(0)
    matrix = userWineRatings.to_numpy()
    userRatingsMean = np.mean(matrix, axis=1)
    userMeanMatrix = matrix - userRatingsMean.reshape(-1, 1)

    U, sigma, Vt = svds(userMeanMatrix, k=12)
    sigma = np.diag(sigma)
    SVDUserRatingPredictions = np.dot(np.dot(U, sigma), Vt) + userRatingsMean.reshape(
        -1, 1
    )
    SVDPredictions_df = pd.DataFrame(
        SVDUserRatingPredictions, columns=userWineRatings.columns
    )

    alredayRated, predictions = recommend_wines(
        SVDPredictions_df, userID, winesData, filteredReviews, num
    )
    return list(predictions["wineID"])[:num]


def find_sim_wine(df, sorted_ind, wineID, top_n=10):
    wineNames = df[df["wineID"] == wineID]
    nameIndexes = wineNames.index.values
    similarWineIndexes = sorted_ind[nameIndexes, : (top_n + 1)]
    similarWineIndexes = similarWineIndexes.reshape(-1)
    result = df.iloc[similarWineIndexes].copy()
    result.drop([wineID], inplace=True)
    return result


def recommend_wines(SVDPredictions_df, userID, winesData, ratingsData, num=5):
    sorted_user_predictions = SVDPredictions_df.iloc[userID].sort_values(
        ascending=False
    )
    userData = ratingsData[ratingsData.userID == userID]
    reviewedWines = userData.merge(winesData, on="wineID").sort_values(
        ["rating"], ascending=False
    )
    recommendations = winesData[~winesData["wineID"].isin(reviewedWines["wineID"])]
    recommendations = recommendations.merge(
        pd.DataFrame(sorted_user_predictions).reset_index(), on="wineID"
    )
    recommendations = (
        recommendations.rename(columns={userID: "Predictions"})
        .sort_values("Predictions", ascending=False)
        .iloc[:num, :]
    )

    return reviewedWines, recommendations


@router.get("/update")
async def update_recommendation_files(request: Request):
    global reviewData, winesData, countVect, tagsMat, tagsSim, tagsSimSortedInd
    reviewData = pd.read_csv(REVIEWS_DATA_URL)
    winesData = pd.read_csv(WINES_DATA_URL)
    countVect = CountVectorizer(min_df=0, ngram_range=(1, 2))
    tagsMat = countVect.fit_transform(winesData["tags"])
    tagsSim = cosine_similarity(tagsMat, tagsMat)
    tagsSimSortedInd = tagsSim.argsort()[:, ::-1]
    print("Recommendation Files have been successfully updated.")
    print(datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"))
    response = JSONResponse(content="Update Success")
    response.status_code = 200
    return response
