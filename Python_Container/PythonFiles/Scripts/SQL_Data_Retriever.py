import os
import mysql.connector
from decimal import Decimal
from datetime import date, datetime


def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "db"),
        user=os.environ.get("DB_USER", "appuser"),
        password=os.environ.get("DB_PASSWORD", "apppassword"),
        database=os.environ.get("DB_NAME", "transportation_db")
    )


def make_json_safe(value):
    """
    Recursively convert MySQL/Python values into JSON-serializable values.
    """
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {key: make_json_safe(val) for key, val in value.items()}

    return value


def get_all_maps():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT map_id, map_name
            FROM maps
            ORDER BY map_id ASC
        """)
        maps = cursor.fetchall()

        return make_json_safe({
            "success": True,
            "maps": maps
        })

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_map_landmarks(map_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT map_id, map_name
            FROM maps
            WHERE map_id = %s
        """, (map_id,))
        map_row = cursor.fetchone()

        if not map_row:
            return {
                "success": False,
                "error": f"Map with map_id {map_id} not found."
            }

        cursor.execute("""
            SELECT
                landmark_id,
                landmark_name,
                type,
                abbreviation,
                latitude,
                longitude
            FROM landmarks
            WHERE map_id = %s
            ORDER BY landmark_name ASC
        """, (map_id,))
        landmarks = cursor.fetchall()

        return make_json_safe({
            "success": True,
            "map": map_row,
            "landmarks": landmarks
        })

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_map_bus_lines(map_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT map_id, map_name
            FROM maps
            WHERE map_id = %s
        """, (map_id,))
        map_row = cursor.fetchone()

        if not map_row:
            return {
                "success": False,
                "error": f"Map with map_id {map_id} not found."
            }

        cursor.execute("""
            SELECT
                bl.bus_line_id,
                bl.line_code,
                bl.flat_price
            FROM bus_lines bl
            WHERE bl.map_id = %s
            ORDER BY bl.line_code ASC
        """, (map_id,))
        bus_lines = cursor.fetchall()

        for line in bus_lines:
            cursor.execute("""
                SELECT
                    bls.stop_order,
                    l.landmark_id,
                    l.landmark_name,
                    l.abbreviation,
                    l.latitude,
                    l.longitude
                FROM bus_line_stops bls
                INNER JOIN landmarks l
                    ON bls.station_landmark_id = l.landmark_id
                WHERE bls.bus_line_id = %s
                ORDER BY bls.stop_order ASC
            """, (line["bus_line_id"],))
            line["stops"] = cursor.fetchall()

        return make_json_safe({
            "success": True,
            "map": map_row,
            "bus_lines": bus_lines
        })

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

def get_map_train_lines(map_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT map_id, map_name
            FROM maps
            WHERE map_id = %s
        """, (map_id,))
        map_row = cursor.fetchone()

        if not map_row:
            return {
                "success": False,
                "error": f"Map with map_id {map_id} not found."
            }

        cursor.execute("""
            SELECT
                tl.train_line_id,
                tl.line_code
            FROM train_lines tl
            WHERE tl.map_id = %s
            ORDER BY tl.line_code ASC
        """, (map_id,))
        train_lines = cursor.fetchall()

        for line in train_lines:
            cursor.execute("""
                SELECT
                    tls.stop_order,
                    l.landmark_id,
                    l.landmark_name,
                    l.abbreviation,
                    l.latitude,
                    l.longitude
                FROM train_line_stops tls
                INNER JOIN landmarks l
                    ON tls.station_landmark_id = l.landmark_id
                WHERE tls.train_line_id = %s
                ORDER BY tls.stop_order ASC
            """, (line["train_line_id"],))
            line["stops"] = cursor.fetchall()

            cursor.execute("""
                SELECT
                    tlf.train_line_fee_id,
                    tlf.from_station_landmark_id,
                    lf.landmark_name AS from_station_name,
                    tlf.to_station_landmark_id,
                    lt.landmark_name AS to_station_name,
                    tlf.price
                FROM train_line_fees tlf
                INNER JOIN landmarks lf
                    ON tlf.from_station_landmark_id = lf.landmark_id
                INNER JOIN landmarks lt
                    ON tlf.to_station_landmark_id = lt.landmark_id
                WHERE tlf.train_line_id = %s
                ORDER BY lf.landmark_name ASC, lt.landmark_name ASC
            """, (line["train_line_id"],))
            line["fees"] = cursor.fetchall()

        return make_json_safe({
            "success": True,
            "map": map_row,
            "train_lines": train_lines
        })

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
def get_map_preview(map_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT map_id, map_name
            FROM maps
            WHERE map_id = %s
        """, (map_id,))
        map_row = cursor.fetchone()

        if not map_row:
            return {
                "success": False,
                "error": f"Map with map_id {map_id} not found."
            }

        cursor.execute("""
            SELECT
                landmark_id,
                landmark_name,
                type,
                abbreviation,
                latitude,
                longitude
            FROM landmarks
            WHERE map_id = %s
            ORDER BY landmark_name ASC
        """, (map_id,))
        landmarks = cursor.fetchall()

        cursor.execute("""
            SELECT
                bl.bus_line_id,
                bl.line_code,
                bl.flat_price
            FROM bus_lines bl
            WHERE bl.map_id = %s
            ORDER BY bl.line_code ASC
        """, (map_id,))
        bus_lines = cursor.fetchall()

        for line in bus_lines:
            cursor.execute("""
                SELECT
                    bls.stop_order,
                    l.landmark_id,
                    l.landmark_name,
                    l.abbreviation,
                    l.latitude,
                    l.longitude
                FROM bus_line_stops bls
                INNER JOIN landmarks l
                    ON bls.station_landmark_id = l.landmark_id
                WHERE bls.bus_line_id = %s
                ORDER BY bls.stop_order ASC
            """, (line["bus_line_id"],))
            line["stops"] = cursor.fetchall()

        cursor.execute("""
            SELECT
                tl.train_line_id,
                tl.line_code
            FROM train_lines tl
            WHERE tl.map_id = %s
            ORDER BY tl.line_code ASC
        """, (map_id,))
        train_lines = cursor.fetchall()

        for line in train_lines:
            cursor.execute("""
                SELECT
                    tls.stop_order,
                    l.landmark_id,
                    l.landmark_name,
                    l.abbreviation,
                    l.latitude,
                    l.longitude
                FROM train_line_stops tls
                INNER JOIN landmarks l
                    ON tls.station_landmark_id = l.landmark_id
                WHERE tls.train_line_id = %s
                ORDER BY tls.stop_order ASC
            """, (line["train_line_id"],))
            line["stops"] = cursor.fetchall()

            cursor.execute("""
                SELECT
                    tlf.train_line_fee_id,
                    tlf.from_station_landmark_id,
                    lf.landmark_name AS from_station_name,
                    tlf.to_station_landmark_id,
                    lt.landmark_name AS to_station_name,
                    tlf.price
                FROM train_line_fees tlf
                INNER JOIN landmarks lf
                    ON tlf.from_station_landmark_id = lf.landmark_id
                INNER JOIN landmarks lt
                    ON tlf.to_station_landmark_id = lt.landmark_id
                WHERE tlf.train_line_id = %s
                ORDER BY lf.landmark_name ASC, lt.landmark_name ASC
            """, (line["train_line_id"],))
            line["fees"] = cursor.fetchall()

        return make_json_safe({
            "success": True,
            "map": map_row,
            "landmarks": landmarks,
            "bus_lines": bus_lines,
            "train_lines": train_lines
        })

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()