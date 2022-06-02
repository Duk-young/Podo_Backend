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
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from typing import List
from PIL import Image
from tempfile import TemporaryFile

router = APIRouter(
    prefix="/s3upload",
    tags=["s3upload"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Operation forbidden"},
        204: {"description": "No content found"},        
    },
)


@router.post("")
async def s3_upload_files(
    request: Request, files: List[UploadFile] = File(...), paths: List[str] = Form(...)
):
    # TODO API test needed
    directory = ""
    url = paths[0].split("/")
    for i in range(len(url) - 1):
        directory += url[i] + "/"
    try:
        if (
            directory_exists(request, directory) == False
        ):  # Create directory if theres no directory exists for the path
            request.app.s3_bucket.put_object(Body="", Key=directory)
        for i in range(len(files)):
            fp = TemporaryFile()  # Temp file space
            extension = str(files[i].filename.split(".")[1]).lower()
            print("ext =", extension)
            if not extension.lower().endswith(
                ("png", "jpeg", "tiff", "bmp", "gif")
            ):  # set to jpeg if the file format is not supported
                extension = "jpeg"
            print("after ext check =", extension)
            img = Image.open(files[i].file)  # file open
            img.save(fp, extension, optimize=True)

            fp.seek(0)  # set image to start point
            imgToUpload = fp.read()
            key = paths[i]
            request.app.s3_bucket.put_object(Body=imgToUpload, Key=key)
    except Exception as e:
        print("An Error occured during s3 upload process.")
        print(e)
        raise HTTPException(
            status_code=403, detail="You can not upload the images at the moment"
        )
    return True


def directory_exists(request: Request, path: str):  # check if directory exists
    if not path.endswith("/"):
        path = path + "/"
    for dir in request.app.s3_bucket.objects.filter(Prefix=path):
        return True
    return False
