FROM python:3-alpine

RUN apk add --update --no-cache g++ gcc libxslt-dev unrar

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

EXPOSE 7897

ENTRYPOINT [ "python" ]

CMD [ "server.py" ]