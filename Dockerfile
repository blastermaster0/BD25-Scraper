FROM python:3-alpine

ARG BUILD_DATE
ARG VCS_REF


RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

# Expose the Flask port
EXPOSE 5000

ENTRYPOINT [ "python" ]

CMD [ "app.py" ]