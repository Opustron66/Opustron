FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
CMD ["python", "-c", "import chronicle; print(chronicle.__version__)"]
