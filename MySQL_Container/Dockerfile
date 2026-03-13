FROM mysql:8.0

# Copy the initialization script to the docker-entrypoint-initdb.d directory
# This script will automatically run on container startup if the DB is empty
COPY ./MySQLFiles/init.sql /docker-entrypoint-initdb.d/

# Expose the default MySQL port
EXPOSE 3306