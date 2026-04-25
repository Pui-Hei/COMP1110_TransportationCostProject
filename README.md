# COMP1110 Transportation Cost Project

## Project Overview
This repository contains a containerized transportation cost and route-planning system built for the COMP1110 project. The application uses:
- a MySQL database service to store transport maps and route metadata
- an Nginx reverse proxy and static frontend pages
- a Python-based backend API for data import, queries, and path calculation

## Technology Stack
- Language: Python 3.x for backend code and HTML/CSS/JavaScript for frontend pages.
- Execution environment: Docker containers orchestrated via Docker Compose.
- Runtime services:
  - MySQL database in `MySQL_Container`
  - Flask-based Python API in `Python_Container`
  - Nginx static server and reverse proxy in `Nginx_Container`
- No compilation step is required for the Python or frontend code.
- Setup is handled via Docker and Docker Compose, with `docker-compose.yml` defining the container topology.

## Repository Structure

### Root
- `docker-compose.yml`
  - Orchestrates the three containers: MySQL, Nginx, and Python.

### `MySQL_Container/`
- `Dockerfile`
  - Builds the MySQL database container.
- `MySQLFiles/init.sql`
  - Creates the database schema and tables used by the application.
  - Defines the `maps`, `landmarks`, `train_lines`, `train_line_stops`, `train_line_fees`, `bus_lines`, and `bus_line_stops` tables.

### `Nginx_Container/`
- `Dockerfile`
  - Builds the Nginx container.
- `NginxFiles/nginx.conf`
  - Configures Nginx as a static file server and reverse proxy.
  - Routes frontend requests to the appropriate static HTML pages.
  - Forwards API requests such as `/import-map-data`, `/maps`, `/best-path`, and `/health` to the Python backend.

### `Nginx_Container/NginxFiles/html/`
- `index.html`
  - Main frontend landing page for the transportation app.
- `index_depricate.html`
  - Deprecated version of the landing page.
- `CSVImporter.html`, `CSVImporter.css`, `CSVImporter.js`
  - Frontend page for uploading CSV map data to the backend.
- `MapPathQuery.html`, `MapPathQuery.css`, `MapPathQuery.js`
  - User interface for querying best routes between landmarks.
- `MapPreviewer.html`, `MapPreviewer.css`, `MapPreviewer.js`
  - Visualization page for previewing maps and network topology.
- `EndpointTester.html`
  - Utility page for manually testing API endpoints.

### `Python_Container/`
- `Dockerfile`
  - Builds the Python backend container.
- `PythonFiles/`
  - Contains backend scripts, helper modules, generated data, and utilities.

#### `PythonFiles/Scripts/`
- `app.py`
  - External Flask application entry point exposing the REST API.
  - Implements health checks, map import endpoints, and route query endpoints.
- `local.py`
  - External command-line interface entry point for loading map CSVs, summarizing stored maps, listing landmarks, and querying journeys locally.
- `CSV_to_SQL.py`
  - Core logic module that reads and validates the CSV files.
  - Converts input CSV rows into database records and inserts them into MySQL.
- `SQL_Data_Retriever.py`
  - Core logic module that queries the MySQL database for map metadata, landmarks, and other stored data.
  - Supports list, lookup, and detailed retrieval operations.
- `Transportation_Path_Calculation.py`
  - Core logic module that implements pathfinding and transport optimization logic.
  - Supports different algorithms and optimization targets such as cheapest, fastest, and least transfers.
- `DataCreator.ipynb`
  - Notebook for creating or exploring sample datasets and map scenarios.

#### `PythonFiles/Data/`
- CSV files for map imports, sample scenarios, and output data.

## Installation
- Ensure Docker and Docker Compose are installed on the host machine.
- Open a terminal in the project root directory where `docker-compose.yml` is located.
- Run:
  - `docker-compose up --build`
- This command builds and starts the MySQL, Python API, and Nginx containers.
- The Python API uses environment variables defined in `docker-compose.yml` to connect to the MySQL service.

## Usage
- Frontend via port 80:
  - Open a browser and navigate to `http://localhost/`.
  - Use the provided HTML pages to upload CSV map data, query routes, and preview maps.
- CLI via Python container:
  - Run the local command line client inside the Python service with:
    - `docker-compose exec api python PythonFiles/Scripts/local.py`
  - This starts the local CLI tool for loading CSV maps, viewing stored maps, listing landmarks, and querying journeys.


