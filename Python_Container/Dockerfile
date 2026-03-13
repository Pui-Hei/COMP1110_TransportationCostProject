FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install system dependencies (useful for building certain python packages)
RUN apt-get update && apt-get install -y gcc default-libmysqlclient-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# You can also use a requirements.txt file here if you prefer: COPY requirements.txt . && pip install -r requirements.txt
RUN pip install --no-cache-dir Flask Flask-RESTful mysql-connector-python jupyter pandas

# Expose Flask port and Jupyter Notebook port
EXPOSE 5000
EXPOSE 8888

# Command to run both Jupyter Notebook (background) and Flask API (foreground)
# Make sure your main flask script is located at /app/Scripts/app.py
CMD jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password='' & \
    python Scripts/app.py