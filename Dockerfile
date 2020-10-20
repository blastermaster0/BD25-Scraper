FROM python:3.8-alpine

RUN apk add --update g++ gcc libxslt-dev make

ADD https://www.rarlab.com/rar/unrarsrc-5.9.1.tar.gz /tmp/
WORKDIR /tmp/
RUN tar -xzf unrarsrc-5.9.1.tar.gz && cd unrar && make lib && make install-lib

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip3 install -r requirements.txt

COPY . /usr/src/app

ENV UNRAR_LIB_PATH /usr/lib/libunrar.so

ENTRYPOINT [ "python" ]

CMD [ "server.py" ]