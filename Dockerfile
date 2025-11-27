# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (adb is needed for device interaction if running in privileged mode or remote adb)
RUN apt-get update && apt-get install -y android-tools-adb && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Create uploads directory
RUN mkdir -p apks

# Make port 8791 available to the world outside this container
EXPOSE 8791

# Run main.py when the container launches
CMD ["python", "main.py"]
