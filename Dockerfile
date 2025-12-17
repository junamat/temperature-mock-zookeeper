FROM python:3.11-slim

WORKDIR /zookeeper-enjoyers

COPY requirements.txt .

RUN pip install --trusted-host pypi.python.org -r requirements.txt

COPY ./main.py /zookeeper-enjoyers
COPY ./init_config.py /zookeeper-enjoyers


ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]

CMD ["python", "main.py"]