# Use an official Python runtime as a parent image
FROM python:3.9-alpine

# Set the working directory in the container to /jankbot
WORKDIR /jankbot2

# Copy the current directory contents into the container at /jankbot
COPY . /jankbot2
RUN pip install --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /jankbot2/requirements.txt
RUN apk add --no-cache ffmpeg

# Run mainio.py when the container launches
CMD ["python", "./main.py"]