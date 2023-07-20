# syntax=docker/dockerfile:1

FROM python:3.10

LABEL net.ftawesome.home.version='2023.07.17.1'

WORKDIR /opt/

ADD ./ /opt/
RUN pip install misaka psutil requests feedgen tornado urllib3 pytz bs4
RUN python -m pip install git+https://github.com/pytube/pytube

CMD python /opt/podtube.py
