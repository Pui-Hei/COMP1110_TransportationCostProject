import os
from flask import Flask
from flask_restful import Api, Resource
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
api = Api(app)

class HealthCheck(Resource):
    def get(self):
        # Base status
        response = {
            "status": "healthy",
            "api": "running"
        }

        # Attempt to connect to the MySQL database using environment variables
        # defined in your docker-compose.yml
        try:
            connection = mysql.connector.connect(
                host=os.environ.get('DB_HOST', 'db'),
                user=os.environ.get('DB_USER', 'appuser'),
                password=os.environ.get('DB_PASSWORD', 'apppassword'),
                database=os.environ.get('DB_NAME', 'transportation_db')
            )
            
            if connection.is_connected():
                response["database"] = "connected"
                connection.close()
                
        except Error as e:
            response["database"] = "disconnected"
            response["error"] = str(e)
            response["status"] = "degraded"

        return response, 200

class Home(Resource):
    def get(self):
        return {"message": "Welcome to the Transportation Cost API!"}, 200

# Map the resources to URLs
api.add_resource(Home, '/')
api.add_resource(HealthCheck, '/health')

if __name__ == '__main__':
    # host='0.0.0.0' is required for Docker so the app is accessible outside the container
    app.run(host='0.0.0.0', port=5000, debug=True)