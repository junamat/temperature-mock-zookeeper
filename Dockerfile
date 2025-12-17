FROM python:3.11-slim

WORKDIR /zookeeper-enjoyers

COPY requirements.txt .

RUN pip install --trusted-host pypi.python.org -r requirements.txt

COPY ./main.py /zookeeper-enjoyers
COPY ./init_config.py /zookeeper-enjoyers

CMD ["python", "main.py"]