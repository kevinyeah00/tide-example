if [ $(uname -m) == "x86_64" ]; then
    ARCH="amd64"
else
    ARCH="arm64"
fi

APP_NAME="facenet-base"
IMAGE_NAME="10.208.104.3:5000/zhengsj/tide/$APP_NAME:$ARCH"

docker build -t $IMAGE_NAME -f base.Dockerfile .
docker push $IMAGE_NAME
# docker image prune -f