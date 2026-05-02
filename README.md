# COMP1110 Transportation Cost Project

## Project Overview
This repository contains a containerized transportation cost and route-planning system built for the COMP1110 project. The application uses:
- a MySQL database service to store transport maps and route metadata
- an Nginx reverse proxy and static frontend pages
- a Python-based backend API for data import, queries, and path calculation

## Technology Stack
- Language: Python 3.9 for backend code and HTML/CSS/JavaScript for frontend pages.
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
  - First start services from the project root:
    - `docker-compose up --build`
  - In a second terminal, run the local command line client inside the Python service:
    - `docker-compose exec api python Scripts/local.py`
  - Alternative (using the container name from `docker-compose.yml`):
    - `docker exec -it python_flask_api bash`
    - `python Scripts/local.py`
  - This starts the local CLI tool for loading CSV maps, viewing stored maps, listing landmarks, and querying journeys.

### CLI Guide

The command-line interface in `Python_Container/PythonFiles/Scripts/local.py` provides an interactive way to exercise the same backend features that are available in the GUI. After starting the containers, you can enter the Python service and launch the CLI with either `docker-compose exec api python Scripts/local.py` or `docker exec -it python_flask_api bash` followed by `python Scripts/local.py`.

Inside the CLI, the menu offers four main actions. Option 1 imports map data from CSV files into the database. Option 2 lists the loaded networks so you can confirm available map IDs. Option 3 displays all landmarks for a selected map, which helps verify whether the imported network was built correctly. Option 4 opens the journey query flow, where you can provide a map ID, origin, destination, available transport modes, optimization mode, algorithm choice, walking limit, beam width, and number of results to display. This allows testing both the general routing flow and specific preferences such as `fastest`, `cheapest`, `least_transfer`, and `fewest_segments` from the terminal without using the browser interface.

For a quick workflow, the recommended sequence is to start the stack with `docker-compose up --build`, import one of the provided sample datasets, and then use the journey query option to compare the CLI output with the GUI results. The CLI prints the total time, total cost, number of segments, number of transfers, and walking time used for each returned journey, so it is suitable for verifying both primary and alternative routes.

## CSV Formats
The importer expects four CSV files. Column names must match exactly and station names must align with the Landmarks file.

- Landmarks CSV (e.g., `DefaultLandmark.csv`)
  - Columns: `Landmark_Name`, `Type`, `Abbreviation`, `Latitude`, `Longitude`

- Train Lines CSV (e.g., `DefaultTrainLines.csv`)
  - Columns: `Line_ID`, `Stop_Order`, `Station_Name`

- Train Fees CSV (e.g., `DefaultTrainFees.csv`)
  - Columns: `Line_ID`, `From_Station`, `To_Station`, `Price`

- Bus Lines CSV (e.g., `DefaultBusLines.csv`)
  - Columns: `Line_ID`, `Price`, `Stop_Order`, `Station_Name`

Notes:
- `Stop_Order` should be an integer.
- `Price`, `Latitude`, and `Longitude` should be numeric.
- Empty files or header-only files will be rejected.


## Sample Test Cases

These test cases evaluate the multimodal route planning system's performance across various algorithms and constraints.

---

### Dataset Information

To run these test cases, load the correct map: UserScenario. Use the following data files in `Python_Container/PythonFiles/Data/`.:
*   Landmarks: UserScenario_Landmarks.csv
*   Train Lines: UserScenario_TrainLines.csv
*   Train Fees: UserScenario_TrainFees.csv
*   Bus Lines: UserScenario_BusLines.csv

---

### Test Scenarios

#### 1. Fastest Route and Algorithm Comparison
Scenario: Peter is in a hurry and needs the quickest path from Dog 50 Recreation Park to Egg 19 Train Station.

*   Execution 1 (Greedy):
    *   Transport Modes: Train (Checked), Bus (Checked), Taxi (Checked), On Foot (Checked)
    *   Optimization: Fastest
    *   Algorithm: Greedy
    *   Beam Width: 15 | Top K: 5 | Max Walk Time: 15 min
    *   Result: Identified multiple routes; the best path found was 56.56 min.
*   Execution 2 (Dijkstra):
    *   Transport Modes: Train (Checked), Bus (Checked), Taxi (Checked), On Foot (Checked)
    *   Optimization: Fastest
    *   Algorithm: Dijkstra
    *   Beam Width: 2 | Top K: 5 | Max Walk Time: 15 min
    *   Result: Found the mathematically optimal path of 40.61 min.

#### 2. Constraint Testing (Walking and Transport Modes)
Scenario: Peter wants the Cheapest route from Grape 54 Train Station to Dog 41 Bus Station without using a taxi.

*   Execution 1 (Strict Walk):
    *   Transport Modes: Train (Checked), Bus (Checked), Taxi (Unchecked), On Foot (Checked)
    *   Optimization: Cheapest
    *   Algorithm: A Star
    *   Beam Width: 5 | Top K: 5 | Max Walk Time: 5 min
    *   Result: Failed. No valid path found due to restricted walking time.
*   Execution 2 (Relaxed Walk):
    *   Transport Modes: Train (Checked), Bus (Checked), Taxi (Unchecked), On Foot (Checked)
    *   Optimization: Cheapest
    *   Algorithm: A Star
    *   Beam Width: 5 | Top K: 5 | Max Walk Time: 30 min
    *   Result: Success. Found a path costing $20.51 with a travel time of 67.85 min.

#### 3. Optimization for Minimum Transfers
Scenario: Peter travels from Dog 22 Residential Building to Apple 2 Shopping Mall and wants to avoid changing vehicles.

*   Execution 1 (With Taxi):
    *   Transport Modes: Train (Checked), Bus (Checked), Taxi (Checked), On Foot (Checked)
    *   Optimization: Least Transfer
    *   Algorithm: Dijkstra
    *   Beam Width: 50 | Top K: 3 | Max Walk Time: 60 min
    *   Result: Returns a direct taxi-only route with 0 transfers.
*   Execution 2 (Public Transport Only):
    *   Transport Modes: Train (Checked), Bus (Checked), Taxi (Unchecked), On Foot (Checked)
    *   Optimization: Least Transfer
    *   Algorithm: Dijkstra
    *   Beam Width: 50 | Top K: 3 | Max Walk Time: 60 min
    *   Result: Generates a multimodal route with 3 transfers and 16 steps.

---

> Note: Results may vary for non-deterministic algorithms, such as the Greedy algorithm, which does not guarantee the same globally optimal solution in every execution.
