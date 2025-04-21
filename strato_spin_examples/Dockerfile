FROM python:3.12-slim

WORKDIR /app/strato_spin_examples

# Install Poetry
RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.create false

# # Copy pyproject.toml and poetry.lock (if exists)
# COPY pyproject.toml poetry.lock* ./

# # Install dependencies (excluding strato-spin, which will be added as path)
# RUN poetry install --no-root

# # Install the project
# RUN poetry install
