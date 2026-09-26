FROM python:3.12-slim

# Install dependencies once at build time, not on every container run.
# Add more test-repo dependencies here as new benchmark repos are added.
RUN pip install --no-cache-dir pytest requests

WORKDIR /repo