FROM ubuntu:22.04

ENV SRV 0

RUN apt-get update
RUN apt-get install -y --no-install-recommends python3 python3-pip

WORKDIR /opt/pavlov-server/praefectus/

RUN mkdir /opt/pavlov-server/praefectus/logs

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python3","./main.py"]