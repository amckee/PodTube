# syntax=docker/dockerfile:1

FROM python:3.10

LABEL net.ftawesome.home.version="2023.04.07.01"

WORKDIR /opt/

ADD ./ /opt/
RUN pip install misaka psutil requests requests_html feedgen pytube3 tornado urllib3 pytz

CMD python /opt/podtube.py
