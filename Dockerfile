# syntax=docker/dockerfile:1

FROM --platform=linux/amd64 python:3.10
FROM --platform=linux/arm64 python:3.10
FROM --platform=linux/arm/v7 python:3.10

LABEL net.ftawesome.home.version="2023.04.07.04"

WORKDIR /opt/

ADD ./ /opt/
RUN pip install misaka psutil requests requests_html feedgen pytube3 tornado urllib3 pytz

CMD python /opt/podtube.py
