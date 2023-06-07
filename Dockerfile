# syntax=docker/dockerfile:1

FROM python:3.10

<<<<<<< HEAD
LABEL net.ftawesome.home.version='2023.05.16.1'
=======
LABEL net.ftawesome.home.version='2023.06.06.1'
>>>>>>> 8c5a834 (Updated version)

WORKDIR /opt/

ADD ./ /opt/
RUN pip install misaka psutil requests feedgen pytube tornado urllib3 pytz bs4

CMD python /opt/podtube.py
