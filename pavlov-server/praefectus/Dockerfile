FROM python:3

ENV SRV 0

RUN apt-get update
RUN apt-get install -y --no-install-recommends

WORKDIR /opt/pavlov-server/praefectus/

RUN mkdir /opt/pavlov-server/praefectus/logs

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python","./main.py"]