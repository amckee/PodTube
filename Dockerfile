# syntax=docker/dockerfile:1

FROM python:3.10

LABEL net.ftawesome.home.version='2025.03.26.1'

WORKDIR /opt/

ADD ./ /opt/
RUN apt update
RUN apt install -y nano less
RUN pip install -r requirements.txt
RUN mkdir -p  /usr/local/lib/python3.10/site-packages/pytubefix/__cache__/
# RUN python -m pip install git+https://github.com/pytube/pytube

CMD ["python", "/opt/podtube.py"]
