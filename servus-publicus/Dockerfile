FROM python:3

RUN apt-get update
RUN apt-get install -y --no-install-recommends

WORKDIR /opt/servus-publicus/

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

COPY cron/generate-events-cron /etc/cron.d/generate-events-cron
COPY cron/generate-ranks-cron /etc/cron.d/generate-ranks-cron
COPY cron/generate-reminder-cron /etc/cron.d/generate-reminder-cron
COPY cron/generate-stats-cron /etc/cron.d/generate-stats-cron

CMD ["python","./main.py"]