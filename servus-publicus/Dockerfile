FROM python:3

RUN apt-get update
RUN apt-get install -y --no-install-recommends

WORKDIR /opt/servus-publicus/

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

COPY cron/events-cron /etc/cron.d/events-cron
COPY cron/ranks-cron /etc/cron.d/ranks-cron
COPY cron/reminder-cron /etc/cron.d/reminder-cron
COPY cron/stats-cron /etc/cron.d/stats-cron

CMD ["python","./main.py"]