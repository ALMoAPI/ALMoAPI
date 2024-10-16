# Use an official CUDA runtime with Ubuntu as a parent image
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    python3.11 \
    python3-pip \
    rustc \
    cargo\
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

# Set the working directory in the container
WORKDIR /app

# Get requirements
COPY pyproject.toml .

# Install packages specified in pyproject.toml cu121
RUN pip3 install --no-cache-dir .[cu121]
RUN pip3 install --no-cache-dir .[extras]
RUN pip3 install --no-cache-dir .[redis]

RUN rm pyproject.toml

# Copy the current directory contents into the container
COPY almoapi .

# Make port 5000 available to the world outside this container
EXPOSE 5000

ENV ALMOAPI_NETWORK_HOST=0.0.0.0

# Set the entry point
ENTRYPOINT ["python3", "start.py"]
