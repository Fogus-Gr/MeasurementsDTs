FROM python:3.9-slim
RUN apt-get update && apt-get install -y procps
COPY /test_app.py /test_app.py
CMD ["python", "/test_app.py"]
