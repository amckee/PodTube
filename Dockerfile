# syntax=docker/dockerfile:1

FROM python:3.12

LABEL net.ftawesome.home.version='2026.01.03.1'

WORKDIR /opt/

ADD ./ /opt/
RUN apt update
RUN apt -y upgrade
# RUN apt install -y nano less # tools useful for in-container debugging
RUN pip install -r requirements.txt
# RUN pip install git+https://github.com/pytube/pytube
# RUN pip install git+https://github.com/felipeucelli/pytubefix.git@sig-nsig
RUN pip install git+https://github.com/JuanBindez/pytubefix.git@dev
RUN mkdir -p  /usr/local/lib/python3.12/site-packages/pytubefix/__cache__/

CMD ["python", "/opt/podtube.py"]
