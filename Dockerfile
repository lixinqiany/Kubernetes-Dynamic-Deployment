FROM python:3.9-slim
WORKDIR /app
RUN pip install kubernetes
COPY test.py .
CMD ["python", "test.py"]