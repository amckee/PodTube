# syntax=docker/dockerfile:1

FROM python:3.12

LABEL net.ftawesome.home.version='2026.03.17.1'

WORKDIR /opt/

ADD ./ /opt/
RUN apt update
RUN apt -y upgrade
# RUN apt install -y nano less # tools useful for in-container debugging
RUN pip install -r requirements.txt

# Run this patched commit until it's merged.
RUN pip install git+https://github.com/JuanBindez/pytubefix.git@1e820e076811d96d73f8acdb33f45b64d7614c0a

# Alternate repos for various fixes.
# RUN pip install git+https://github.com/JuanBindez/pytubefix.git@dev
# RUN pip install git+https://github.com/sdrapha/pytubefix.git@patch1
# RUN pip install git+https://github.com/pytube/pytube

RUN mkdir -p  /usr/local/lib/python3.12/site-packages/pytubefix/__cache__/

CMD ["python", "/opt/podtube.py"]
