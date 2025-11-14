# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code into the container
COPY . .

# Define environment variables (if any)
# For example, the port the app will run on. Cloud Run provides the PORT env var.
ENV PORT 8080

# Command to run your application
# Replace main:app with the correct entry point for your application
# e.g., if you run your app with `python main.py`, you might use `CMD ["python", "main.py"]`
# If you are using a web framework like Flask or FastAPI, you'll use gunicorn or similar.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
