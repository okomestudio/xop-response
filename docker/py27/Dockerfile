FROM python:2.7.15-alpine

WORKDIR /code
COPY bin ./bin
COPY src ./src
COPY tests ./tests
COPY .coveragerc requirements-dev.txt requirements.txt setup.py ./
RUN pip install -r requirements-dev.txt && rm -rf ~/.cache/pip
