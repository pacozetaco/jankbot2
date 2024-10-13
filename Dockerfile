# Use an official Python runtime as a parent image
FROM python:3.9-alpine

# Set the working directory in the container to /jankbot2
WORKDIR /jankbot2

# Copy the current directory contents into the container at /jankbot2
COPY . .

# Install system dependencies and Python packages
RUN apk update && \
    apk add --no-cache ffmpeg && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/cache/apk/*

# Run main.py when the container launches
CMD ["python", "./main.py"]
