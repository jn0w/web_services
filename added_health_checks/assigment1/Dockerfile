# ubuntu base image
FROM ubuntu:22.04

# keep apt non interactive
ENV DEBIAN_FRONTEND=noninteractive

# install python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# copy project files
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# start the api
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
