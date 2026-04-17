# syntax=docker/dockerfile:1

FROM python:3.12

LABEL net.ftawesome.home.version='2026.04.06.1'

WORKDIR /opt/

ADD ./ /opt/
RUN apt update
RUN apt -y upgrade
# RUN apt install -y nano less # tools useful for in-container debugging
RUN pip install -r requirements.txt

# Run this patched commit until it's merged.
RUN pip install git+https://github.com/JuanBindez/pytubefix.git@5403c0620e6c512d643a4937566fb812d573b7b3

# Alternate repos for various fixes.
# RUN pip install git+https://github.com/JuanBindez/pytubefix.git@dev
# RUN pip install git+https://github.com/sdrapha/pytubefix.git@patch1
# RUN pip install git+https://github.com/pytube/pytube

RUN mkdir -p  /usr/local/lib/python3.12/site-packages/pytubefix/__cache__/

CMD ["python", "/opt/podtube.py"]
