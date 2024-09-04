# syntax=docker/dockerfile:1

FROM python:3.10

LABEL net.ftawesome.home.version='2024.09.04.4'

WORKDIR /opt/

ADD ./ /opt/
RUN apt update
RUN apt install -y nano
RUN pip install misaka psutil requests feedgen tornado urllib3 pytz bs4 cloudscraper pytubefix
# RUN python -m pip install git+https://github.com/pytube/pytube
RUN patch --ignore-whitespace --fuzz=3 -u /usr/local/lib/python3.10/site-packages/pytube/cipher.py -i /opt/cipher.patch

CMD ["python", "/opt/podtube.py"]
