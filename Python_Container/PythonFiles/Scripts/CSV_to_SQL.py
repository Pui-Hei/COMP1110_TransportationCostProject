import csv
import io
import os
import mysql.connector


def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "db"),
        user=os.environ.get("DB_USER", "appuser"),
        password=os.environ.get("DB_PASSWORD", "apppassword"),
        database=os.environ.get("DB_NAME", "transportation_db")
    )


# =========================================================
# CSV READING
# =========================================================

def read_csv_file(file_obj):
    """
    Accepts a Flask uploaded file or any file-like object.
    Returns a list of dictionaries from the CSV.
    """
    if not file_obj or not hasattr(file_obj, 'read'):
        raise ValueError("Invalid file object provided. Expected a file-like object.")

    content = file_obj.read()

    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    if not str(content).strip():
        raise ValueError("CSV file is empty.")

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV file has no data rows.")
    return rows


def read_all_csv_files(train_lines_file, train_fees_file, landmarks_file, bus_lines_file):
    """
    Reads all 4 CSV files and returns raw rows.
    """
    return {
        "landmarks": read_csv_file(landmarks_file),
        "train_lines": read_csv_file(train_lines_file),
        "train_fees": read_csv_file(train_fees_file),
        "bus_lines": read_csv_file(bus_lines_file)
    }


# =========================================================
# CSV PROCESSING
# =========================================================

def process_landmarks(rows):
    """
    Convert landmark CSV rows into normalized Python dictionaries.
    """
    processed = []
    required_keys = {"Landmark_Name", "Type", "Abbreviation", "Latitude", "Longitude"}

    for i, row in enumerate(rows, start=1):
        if not required_keys.issubset(row.keys()):
            raise ValueError(f"Landmarks CSV missing required columns at row {i}. Required: {required_keys}")
        
        try:
            latitude = float(row["Latitude"])
            longitude = float(row["Longitude"])
        except ValueError:
            raise ValueError(f"Invalid Latitude or Longitude at row {i} in Landmarks CSV. Must be numeric.")

        processed.append({
            "landmark_name": row["Landmark_Name"].strip(),
            "type": row["Type"].strip(),
            "abbreviation": row["Abbreviation"].strip(),
            "latitude": latitude,
            "longitude": longitude
        })

    return processed


def process_train_lines(rows):
    """
    Extract:
    - unique train line codes
    - ordered stop rows
    """
    line_codes = []
    seen = set()
    stops = []
    required_keys = {"Line_ID", "Stop_Order", "Station_Name"}

    for i, row in enumerate(rows, start=1):
        if not required_keys.issubset(row.keys()):
            raise ValueError(f"Train Lines CSV missing required columns at row {i}. Required: {required_keys}")

        line_code = row["Line_ID"].strip()

        if line_code not in seen:
            seen.add(line_code)
            line_codes.append(line_code)

        try:
            stop_order = int(row["Stop_Order"])
        except ValueError:
            raise ValueError(f"Invalid Stop_Order at row {i} in Train Lines CSV. Must be an integer.")

        stops.append({
            "line_code": line_code,
            "stop_order": stop_order,
            "station_name": row["Station_Name"].strip()
        })

    return {
        "line_codes": line_codes,
        "stops": stops
    }


def process_train_fees(rows):
    """
    Convert train fee CSV rows into normalized Python dictionaries.
    """
    processed = []
    required_keys = {"Line_ID", "From_Station", "To_Station", "Price"}

    for i, row in enumerate(rows, start=1):
        if not required_keys.issubset(row.keys()):
            raise ValueError(f"Train Fees CSV missing required columns at row {i}. Required: {required_keys}")

        try:
            price = float(row["Price"])
        except ValueError:
            raise ValueError(f"Invalid Price at row {i} in Train Fees CSV. Must be numeric.")

        processed.append({
            "line_code": row["Line_ID"].strip(),
            "from_station": row["From_Station"].strip(),
            "to_station": row["To_Station"].strip(),
            "price": price
        })

    return processed


def process_bus_lines(rows):
    """
    Extract:
    - unique bus lines with flat price
    - ordered stop rows
    """
    line_prices = {}
    stops = []
    required_keys = {"Line_ID", "Price", "Stop_Order", "Station_Name"}

    for i, row in enumerate(rows, start=1):
        if not required_keys.issubset(row.keys()):
            raise ValueError(f"Bus Lines CSV missing required columns at row {i}. Required: {required_keys}")

        line_code = row["Line_ID"].strip()
        
        try:
            price = float(row["Price"])
            stop_order = int(row["Stop_Order"])
        except ValueError:
            raise ValueError(f"Invalid Price or Stop_Order at row {i} in Bus Lines CSV. Must be numeric.")

        if line_code not in line_prices:
            line_prices[line_code] = price

        stops.append({
            "line_code": line_code,
            "stop_order": stop_order,
            "station_name": row["Station_Name"].strip()
        })

    lines = [
        {"line_code": line_code, "flat_price": price}
        for line_code, price in line_prices.items()
    ]

    return {
        "lines": lines,
        "stops": stops
    }


def process_csv_data(raw_data):
    """
    Process all raw CSV rows into a structured format
    ready for database insertion.
    """
    return {
        "landmarks": process_landmarks(raw_data["landmarks"]),
        "train_lines": process_train_lines(raw_data["train_lines"]),
        "train_fees": process_train_fees(raw_data["train_fees"]),
        "bus_lines": process_bus_lines(raw_data["bus_lines"])
    }


# =========================================================
# DATABASE INSERTION
# =========================================================


def validate_or_create_map(cursor, map_id, map_name):
    map_name = (map_name or "").strip()

    cursor.execute("SELECT map_id, map_name FROM maps WHERE map_id = %s", (map_id,))
    result = cursor.fetchone()

    if result:
        raise ValueError(
            f"Map with map_id {map_id} already exists "
            f"(map_name='{result['map_name']}'). Refusing to insert."
        )

    if not map_name:
        raise ValueError("map_name is required when creating a new map.")

    cursor.execute(
        "INSERT INTO maps (map_id, map_name) VALUES (%s, %s)",
        (map_id, map_name)
    )

    return True


def insert_landmarks(cursor, map_id, landmarks):
    insert_sql = """
        INSERT INTO landmarks (
            map_id, landmark_name, type, abbreviation, latitude, longitude
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """

    select_sql = """
        SELECT landmark_id
        FROM landmarks
        WHERE map_id = %s AND landmark_name = %s
    """

    landmark_id_map = {}
    inserted_count = 0

    for landmark in landmarks:
        cursor.execute(select_sql, (map_id, landmark["landmark_name"]))
        existing = cursor.fetchone()

        if existing:
            landmark_id = existing["landmark_id"]
        else:
            cursor.execute(
                insert_sql,
                (
                    map_id,
                    landmark["landmark_name"],
                    landmark["type"],
                    landmark["abbreviation"],
                    landmark["latitude"],
                    landmark["longitude"]
                )
            )
            landmark_id = cursor.lastrowid
            inserted_count += 1

        landmark_id_map[landmark["landmark_name"]] = landmark_id

    return inserted_count, landmark_id_map


def insert_train_lines(cursor, map_id, line_codes):
    insert_sql = """
        INSERT INTO train_lines (map_id, line_code)
        VALUES (%s, %s)
    """

    select_sql = """
        SELECT train_line_id
        FROM train_lines
        WHERE map_id = %s AND line_code = %s
    """

    train_line_id_map = {}
    inserted_count = 0

    for line_code in line_codes:
        cursor.execute(select_sql, (map_id, line_code))
        existing = cursor.fetchone()

        if existing:
            train_line_id = existing["train_line_id"]
        else:
            cursor.execute(insert_sql, (map_id, line_code))
            train_line_id = cursor.lastrowid
            inserted_count += 1

        train_line_id_map[line_code] = train_line_id

    return inserted_count, train_line_id_map


def insert_train_line_stops(cursor, stops, train_line_id_map, landmark_id_map):
    insert_sql = """
        INSERT INTO train_line_stops (
            train_line_id, stop_order, station_landmark_id
        ) VALUES (%s, %s, %s)
    """

    select_sql = """
        SELECT train_line_stop_id
        FROM train_line_stops
        WHERE train_line_id = %s AND stop_order = %s
    """

    inserted_count = 0

    for stop in stops:
        station_name = stop["station_name"]
        line_code = stop["line_code"]

        if station_name not in landmark_id_map:
            raise ValueError(f"Train stop station '{station_name}' not found in landmarks data.")

        train_line_id = train_line_id_map[line_code]
        station_landmark_id = landmark_id_map[station_name]

        cursor.execute(select_sql, (train_line_id, stop["stop_order"]))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                insert_sql,
                (train_line_id, stop["stop_order"], station_landmark_id)
            )
            inserted_count += 1

    return inserted_count


def insert_train_fees(cursor, fees, train_line_id_map, landmark_id_map):
    insert_sql = """
        INSERT INTO train_line_fees (
            train_line_id, from_station_landmark_id, to_station_landmark_id, price
        ) VALUES (%s, %s, %s, %s)
    """

    select_sql = """
        SELECT train_line_fee_id
        FROM train_line_fees
        WHERE train_line_id = %s
          AND from_station_landmark_id = %s
          AND to_station_landmark_id = %s
    """

    inserted_count = 0

    for fee in fees:
        if fee["from_station"] not in landmark_id_map:
            raise ValueError(f"From_Station '{fee['from_station']}' not found in landmarks data.")
        if fee["to_station"] not in landmark_id_map:
            raise ValueError(f"To_Station '{fee['to_station']}' not found in landmarks data.")
        if fee["line_code"] not in train_line_id_map:
            raise ValueError(f"Train line '{fee['line_code']}' not found in train lines data.")

        train_line_id = train_line_id_map[fee["line_code"]]
        from_station_id = landmark_id_map[fee["from_station"]]
        to_station_id = landmark_id_map[fee["to_station"]]

        cursor.execute(select_sql, (train_line_id, from_station_id, to_station_id))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                insert_sql,
                (train_line_id, from_station_id, to_station_id, fee["price"])
            )
            inserted_count += 1

    return inserted_count


def insert_bus_lines(cursor, map_id, lines):
    insert_sql = """
        INSERT INTO bus_lines (map_id, line_code, flat_price)
        VALUES (%s, %s, %s)
    """

    select_sql = """
        SELECT bus_line_id
        FROM bus_lines
        WHERE map_id = %s AND line_code = %s
    """

    bus_line_id_map = {}
    inserted_count = 0

    for line in lines:
        cursor.execute(select_sql, (map_id, line["line_code"]))
        existing = cursor.fetchone()

        if existing:
            bus_line_id = existing["bus_line_id"]
        else:
            cursor.execute(insert_sql, (map_id, line["line_code"], line["flat_price"]))
            bus_line_id = cursor.lastrowid
            inserted_count += 1

        bus_line_id_map[line["line_code"]] = bus_line_id

    return inserted_count, bus_line_id_map


def insert_bus_line_stops(cursor, stops, bus_line_id_map, landmark_id_map):
    insert_sql = """
        INSERT INTO bus_line_stops (
            bus_line_id, stop_order, station_landmark_id
        ) VALUES (%s, %s, %s)
    """

    select_sql = """
        SELECT bus_line_stop_id
        FROM bus_line_stops
        WHERE bus_line_id = %s AND stop_order = %s
    """

    inserted_count = 0

    for stop in stops:
        station_name = stop["station_name"]
        line_code = stop["line_code"]

        if station_name not in landmark_id_map:
            raise ValueError(f"Bus stop station '{station_name}' not found in landmarks data.")

        bus_line_id = bus_line_id_map[line_code]
        station_landmark_id = landmark_id_map[station_name]

        cursor.execute(select_sql, (bus_line_id, stop["stop_order"]))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                insert_sql,
                (bus_line_id, stop["stop_order"], station_landmark_id)
            )
            inserted_count += 1

    return inserted_count



def insert_processed_map_data(map_id, map_name, processed_data):
    """
    Insert already-processed data into database.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        created_new_map = validate_or_create_map(cursor, map_id, map_name)

        inserted_landmarks, landmark_id_map = insert_landmarks(
            cursor, map_id, processed_data["landmarks"]
        )

        inserted_train_lines, train_line_id_map = insert_train_lines(
            cursor, map_id, processed_data["train_lines"]["line_codes"]
        )

        inserted_train_stops = insert_train_line_stops(
            cursor,
            processed_data["train_lines"]["stops"],
            train_line_id_map,
            landmark_id_map
        )

        inserted_train_fees = insert_train_fees(
            cursor,
            processed_data["train_fees"],
            train_line_id_map,
            landmark_id_map
        )

        inserted_bus_lines, bus_line_id_map = insert_bus_lines(
            cursor, map_id, processed_data["bus_lines"]["lines"]
        )

        inserted_bus_stops = insert_bus_line_stops(
            cursor,
            processed_data["bus_lines"]["stops"],
            bus_line_id_map,
            landmark_id_map
        )

        connection.commit()

        return {
            "success": True,
            "map_id": map_id,
            "map_name": map_name,
            "created_new_map": created_new_map,
            "inserted_landmarks": inserted_landmarks,
            "inserted_train_lines": inserted_train_lines,
            "inserted_train_stops": inserted_train_stops,
            "inserted_train_fees": inserted_train_fees,
            "inserted_bus_lines": inserted_bus_lines,
            "inserted_bus_stops": inserted_bus_stops
        }

    except Exception as e:
        if connection:
            connection.rollback()
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# =========================================================
# MAIN PUBLIC FUNCTION
# =========================================================

def insert_map_data(map_id, map_name, train_lines_file, train_fees_file, landmarks_file, bus_lines_file):

    """
    High-level function:
    1. Read CSV files
    2. Process CSV data
    3. Insert into database
    """
    raw_data = read_all_csv_files(
        train_lines_file=train_lines_file,
        train_fees_file=train_fees_file,
        landmarks_file=landmarks_file,
        bus_lines_file=bus_lines_file
    )

    processed_data = process_csv_data(raw_data)

    return insert_processed_map_data(map_id, map_name, processed_data)