FROM python:3.10-slim


RUN pip install uv

WORKDIR /app/

ADD ./requirements.lock /app/requirements.lock
ADD ./pyproject.toml /app/pyproject.toml
ADD ./README.md /app/README.md

RUN uv pip install --no-cache --system -r requirements.lock

COPY ./app /app
ENV PYTHONPATH=/app

#ADD app/app/root/start-reload.sh /start-reload.sh

