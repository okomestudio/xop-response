FROM python:3.7-slim

WORKDIR /code
COPY bin ./bin
COPY src ./src
COPY tests ./tests
COPY .coveragerc requirements-dev.txt requirements.txt setup.py ./
RUN pip install -r requirements-dev.txt && rm -rf ~/.cache/pip
