FROM python:3

RUN apt-get update
RUN apt-get install -y --no-install-recommends

WORKDIR /opt/servus-publicus/

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python","./main.py"]