FROM python:3.13-slim
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY docker/start-syngonium.sh /usr/local/bin/start-syngonium.sh
RUN chmod +x /usr/local/bin/start-syngonium.sh
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "app.main"]
