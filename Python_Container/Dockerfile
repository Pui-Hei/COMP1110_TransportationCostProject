FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# 1. Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies
RUN pip install --no-cache-dir \
    Flask \
    Flask-RESTful \
    mysql-connector-python \
    jupyter \
    pandas \
    matplotlib

# 3. Expose Flask port and Jupyter Notebook port
EXPOSE 5000
EXPOSE 8888

# 4. Start-up Command
CMD jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password='' & \
    python Scripts/app.py