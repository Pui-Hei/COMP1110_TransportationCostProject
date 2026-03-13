import os
from flask import Flask, request
from flask_restful import Api, Resource
import mysql.connector
from mysql.connector import Error
import CSV_to_SQL
import SQL_Data_Retriever

app = Flask(__name__)
api = Api(app)


class HealthCheck(Resource):
    def get(self):
        response = {
            "status": "healthy",
            "api": "running"
        }
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


class ImportMapData(Resource):
    def post(self):
        try:
            map_id = request.form.get("map_id")
            map_name = request.form.get("map_name", "").strip()

            if not map_id:
                return {
                    "success": False,
                    "error": "Missing required form field: map_id"
                }, 400

            if not map_name:
                return {
                    "success": False,
                    "error": "Missing required form field: map_name"
                }, 400

            try:
                map_id = int(map_id)
            except ValueError:
                return {
                    "success": False,
                    "error": "map_id must be an integer"
                }, 400

            train_lines_file = request.files.get("train_lines")
            train_fees_file = request.files.get("train_fees")
            landmarks_file = request.files.get("landmarks")
            bus_lines_file = request.files.get("bus_lines")

            missing_files = []
            if not train_lines_file:
                missing_files.append("train_lines")
            if not train_fees_file:
                missing_files.append("train_fees")
            if not landmarks_file:
                missing_files.append("landmarks")
            if not bus_lines_file:
                missing_files.append("bus_lines")

            if missing_files:
                return {
                    "success": False,
                    "error": f"Missing required file(s): {', '.join(missing_files)}"
                }, 400

            result = CSV_to_SQL.insert_map_data(
                map_id=map_id,
                map_name=map_name,
                train_lines_file=train_lines_file,
                train_fees_file=train_fees_file,
                landmarks_file=landmarks_file,
                bus_lines_file=bus_lines_file
            )

            if result.get("success"):
                return result, 200
            else:
                return result, 400

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


class MapsList(Resource):
    def get(self):
        result = SQL_Data_Retriever.get_all_maps()

        if result.get("success"):
            return result, 200
        return result, 500


class MapLandmarks(Resource):
    def get(self, map_id):
        result = SQL_Data_Retriever.get_map_landmarks(map_id)

        if result.get("success"):
            return result, 200

        if "not found" in result.get("error", "").lower():
            return result, 404

        return result, 500


class MapBusLines(Resource):
    def get(self, map_id):
        result = SQL_Data_Retriever.get_map_bus_lines(map_id)

        if result.get("success"):
            return result, 200

        if "not found" in result.get("error", "").lower():
            return result, 404

        return result, 500


class MapTrainLines(Resource):
    def get(self, map_id):
        result = SQL_Data_Retriever.get_map_train_lines(map_id)

        if result.get("success"):
            return result, 200

        if "not found" in result.get("error", "").lower():
            return result, 404

        return result, 500

class MapPreview(Resource):
    def get(self, map_id):
        result = SQL_Data_Retriever.get_map_preview(map_id)

        if result.get("success"):
            return result, 200

        if "not found" in result.get("error", "").lower():
            return result, 404

        return result, 500


api.add_resource(Home, '/')
api.add_resource(HealthCheck, '/health')
api.add_resource(ImportMapData, '/import-map-data')
api.add_resource(MapsList, '/maps')
api.add_resource(MapLandmarks, '/maps/<int:map_id>/landmarks')
api.add_resource(MapBusLines, '/maps/<int:map_id>/bus-lines')
api.add_resource(MapTrainLines, '/maps/<int:map_id>/train-lines')
api.add_resource(MapPreview, '/maps/<int:map_id>/preview')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)