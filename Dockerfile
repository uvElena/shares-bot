# syntax=docker/dockerfile:1

FROM python:3.8-slim
WORKDIR /shares-bot
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY run.py run.py
ENV PYTHONUNBUFFERED=1
CMD [ "python3", "run.py"]
