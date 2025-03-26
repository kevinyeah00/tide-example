FROM 10.208.104.3:5000/zhengsj/tide/facenet-base:amd64

ENV PYTHONPATH=/app

COPY . /app

WORKDIR /app/facenet

# CMD ["python", "/app/facenet/predict.py"]

