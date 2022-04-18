FROM ubuntu:20.04

# aws time zone
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get -y install \
    python3.9 \
    python3-pip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY ./app /code/app
COPY ./requirements.txt /code/requirements.txt
ENV AWS_ACCESS_KEY=AKIA4ZEKSAALCJ337W76 \
    AWS_SECRET_KEY=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 \
    AWS_REGION=ap-northeast-2 \
    AWS_BUCKET_NAME=oneego-image-storage \
    AWS_IMAGE_SERVER_URL=https://oneego-image-storage.s3.ap-northeast-2.amazonaws.com/ \
    DB_ADDRESS=mongodb+srv://CSE416:oneego@cluster0.3iyx0.mongodb.net/podo_dev \
    RUNTIME_ENV=dev
RUN python3.9 -m pip install --no-cache-dir --upgrade -r /code/requirements.txt
# 
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT