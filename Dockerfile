FROM python:3.10

ADD ./ /opt/
RUN pip install misaka psutil requests requests_html feedgen pytube3 tornado urllib3 pytz

CMD python /opt/podtube.py
