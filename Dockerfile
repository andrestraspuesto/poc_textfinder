FROM python:3.9.9-slim-buster

RUN apt-get update && apt-get install -y ffmpeg 
RUN pip install --upgrade pip
RUN pip install \
    SpeechRecognition \
    ffmpeg-python \
    redis \
    schedule

WORKDIR /usr/src/app
