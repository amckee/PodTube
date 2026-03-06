# syntax=docker/dockerfile:1

FROM python:3.12

LABEL net.ftawesome.home.version='2026.03.05.3'

WORKDIR /opt/

ADD ./ /opt/
RUN apt update
RUN apt -y upgrade
# RUN apt install -y nano less # tools useful for in-container debugging
RUN pip install -r requirements.txt

RUN pip install git+https://github.com/JuanBindez/pytubefix.git
# https://github.com/romamo/pytubefix/tree/fix/get_initial_function_name
# RUN pip install git+https://github.com/felipeucelli/pytubefix.git@sig-nsig
# RUN pip install git+https://github.com/pytube/pytube
# RUN pip install git+https://github.com/JuanBindez/pytubefix.git@dev

## Allegedly a fix, but it's not working for me
# RUN pip install git+https://github.com/felipeucelli/pytubefix.git@ca8c67f

RUN mkdir -p  /usr/local/lib/python3.12/site-packages/pytubefix/__cache__/

# Temporary fix; manually overwrite this file with the new code from the PR
RUN wget https://raw.githubusercontent.com/romamo/pytubefix/fix/get_initial_function_name/pytubefix/extract.py -O /usr/local/lib/python3.12/site-packages/pytubefix/extract.py

CMD ["python", "/opt/podtube.py"]
