FROM python:3.12-slim
RUN pip install --no-cache-dir flask==2.3.3 Werkzeug==2.3.7 requests prometheus-flask-exporter pymongo
WORKDIR /app
COPY ./app.py /app/app.py
RUN useradd --system --no-create-home app
USER app
CMD ["python","-u", "app.py"]
