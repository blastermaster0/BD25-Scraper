FROM python3.6-alpine3.7

RUN apk add --no-cache gcc musl-dev libxslt-dev && pip3 install pip==10.0.1

RUN pip3 install lxml

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

EXPOSE 7897

ENTRYPOINT [ "python" ]

CMD [ "server.py" ]