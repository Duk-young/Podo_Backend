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
RUN python3.9 -m pip install --no-cache-dir --upgrade -r /code/requirements.txt
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT