FROM python:3.12-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    npm_config_update_notifier=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git bash ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

COPY frontend/package.json frontend/package-lock.json /workspace/frontend/
WORKDIR /workspace/frontend
RUN npm ci

WORKDIR /workspace
COPY . /workspace
CMD ["bash", "/workspace/docker/start-fe.sh"]
