# syntax=docker/dockerfile:1

FROM python:3.10

LABEL net.ftawesome.home.version='2025.04.08.1'

WORKDIR /opt/

ADD ./ /opt/
RUN apt update
RUN apt -y upgrade
RUN apt install -y nano less git
RUN pip install -r requirements.txt
RUN pip install git+https://github.com/felipeucelli/pytubefix.git@new-player
RUN mkdir -p  /usr/local/lib/python3.10/site-packages/pytubefix/__cache__/
# RUN python -m pip install git+https://github.com/pytube/pytube

# Temporary fix from https://github.com/JuanBindez/pytubefix/issues/480
# RUN cd /usr/local/lib/python3.10/site-packages/
# RUN wget https://patch-diff.githubusercontent.com/raw/JuanBindez/pytubefix/pull/481.patch -O yt.patch
# RUN git apply yt.patch

CMD ["python", "/opt/podtube.py"]
