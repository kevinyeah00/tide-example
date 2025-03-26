FROM python:3.7 as builder

RUN mkdir /app

COPY requirements.txt /app

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
    
RUN pip install requests posix_ipc loguru protobuf

RUN pip install -U protobuf==4.21.0

RUN pip install -r /app/requirements.txt

