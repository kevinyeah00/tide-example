FROM python:3.7 as builder

RUN mkdir /app

COPY requirements.txt /app

RUN pip install -r /app/requirements.txt

FROM python:3.7

RUN pip install posix_ipc loguru protobuf

RUN pip install -U protobuf==4.21.0


COPY --from=builder /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages

COPY . /app

ENV PYTHONPATH=/app

# CMD ["python", "/app/facenet/predict.py"]