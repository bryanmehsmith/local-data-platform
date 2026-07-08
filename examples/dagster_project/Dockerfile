FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dagster/app

COPY pyproject.toml setup.py ./
COPY local_data_platform ./local_data_platform

RUN pip install --no-cache-dir -e . dbt-core dbt-trino

ENV DAGSTER_HOME=/opt/dagster/dagster_home
RUN mkdir -p ${DAGSTER_HOME}

EXPOSE 3000 4000
