FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y curl && \
    curl --proto '=https' --tlsv1.2 -sSfL https://sh.vector.dev | bash -s -- -y && \
    ln -s /root/.vector/bin/vector /usr/local/bin/vector && \
    pip install uv --no-cache-dir && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/

#RUN pip install uv

WORKDIR /app/

# todo change to UV, add vector.toml
ADD ./pyproject.toml /app/pyproject.toml
ADD ./README.md /app/README.md

#RUN uv pip install --no-cache --system -r requirements.lock
RUN uv pip install --no-cache --system -r pyproject.toml

COPY ./app /app
ENV PYTHONPATH=/app

#ADD app/app/root/start-reload.sh /start-reload.sh

