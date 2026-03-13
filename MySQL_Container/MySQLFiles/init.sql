CREATE DATABASE IF NOT EXISTS transportation_db;
USE transportation_db;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS bus_line_stops;
DROP TABLE IF EXISTS bus_lines;
DROP TABLE IF EXISTS train_line_fees;
DROP TABLE IF EXISTS train_line_stops;
DROP TABLE IF EXISTS train_lines;
DROP TABLE IF EXISTS landmarks;
DROP TABLE IF EXISTS maps;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE maps (
    map_id INT AUTO_INCREMENT PRIMARY KEY,
    map_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE landmarks (
    landmark_id INT AUTO_INCREMENT PRIMARY KEY,
    map_id INT NOT NULL,
    landmark_name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(20) NOT NULL,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    CONSTRAINT fk_landmarks_map
        FOREIGN KEY (map_id) REFERENCES maps(map_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT uq_landmark_name_per_map
        UNIQUE (map_id, landmark_name),
    INDEX idx_landmarks_map_id (map_id),
    INDEX idx_landmarks_type (type),
    INDEX idx_landmarks_name (landmark_name)
) ENGINE=InnoDB;

CREATE TABLE train_lines (
    train_line_id INT AUTO_INCREMENT PRIMARY KEY,
    map_id INT NOT NULL,
    line_code VARCHAR(50) NOT NULL,
    CONSTRAINT fk_train_lines_map
        FOREIGN KEY (map_id) REFERENCES maps(map_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT uq_train_line_code_per_map
        UNIQUE (map_id, line_code),
    INDEX idx_train_lines_map_id (map_id)
) ENGINE=InnoDB;

CREATE TABLE train_line_stops (
    train_line_stop_id INT AUTO_INCREMENT PRIMARY KEY,
    train_line_id INT NOT NULL,
    stop_order INT NOT NULL,
    station_landmark_id INT NOT NULL,
    CONSTRAINT fk_train_line_stops_line
        FOREIGN KEY (train_line_id) REFERENCES train_lines(train_line_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_train_line_stops_station
        FOREIGN KEY (station_landmark_id) REFERENCES landmarks(landmark_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT uq_train_line_stop_order
        UNIQUE (train_line_id, stop_order),
    CONSTRAINT uq_train_line_station_once
        UNIQUE (train_line_id, station_landmark_id),
    INDEX idx_train_line_stops_line_id (train_line_id),
    INDEX idx_train_line_stops_station_id (station_landmark_id)
) ENGINE=InnoDB;

CREATE TABLE train_line_fees (
    train_line_fee_id INT AUTO_INCREMENT PRIMARY KEY,
    train_line_id INT NOT NULL,
    from_station_landmark_id INT NOT NULL,
    to_station_landmark_id INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_train_line_fees_line
        FOREIGN KEY (train_line_id) REFERENCES train_lines(train_line_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_train_line_fees_from_station
        FOREIGN KEY (from_station_landmark_id) REFERENCES landmarks(landmark_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_train_line_fees_to_station
        FOREIGN KEY (to_station_landmark_id) REFERENCES landmarks(landmark_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT uq_train_line_fee_segment
        UNIQUE (train_line_id, from_station_landmark_id, to_station_landmark_id),
    INDEX idx_train_line_fees_line_id (train_line_id),
    INDEX idx_train_line_fees_from_station (from_station_landmark_id),
    INDEX idx_train_line_fees_to_station (to_station_landmark_id)
) ENGINE=InnoDB;

CREATE TABLE bus_lines (
    bus_line_id INT AUTO_INCREMENT PRIMARY KEY,
    map_id INT NOT NULL,
    line_code VARCHAR(50) NOT NULL,
    flat_price DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_bus_lines_map
        FOREIGN KEY (map_id) REFERENCES maps(map_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT uq_bus_line_code_per_map
        UNIQUE (map_id, line_code),
    INDEX idx_bus_lines_map_id (map_id)
) ENGINE=InnoDB;

CREATE TABLE bus_line_stops (
    bus_line_stop_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_line_id INT NOT NULL,
    stop_order INT NOT NULL,
    station_landmark_id INT NOT NULL,
    CONSTRAINT fk_bus_line_stops_line
        FOREIGN KEY (bus_line_id) REFERENCES bus_lines(bus_line_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_bus_line_stops_station
        FOREIGN KEY (station_landmark_id) REFERENCES landmarks(landmark_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT uq_bus_line_stop_order
        UNIQUE (bus_line_id, stop_order),
    CONSTRAINT uq_bus_line_station_once
        UNIQUE (bus_line_id, station_landmark_id),
    INDEX idx_bus_line_stops_line_id (bus_line_id),
    INDEX idx_bus_line_stops_station_id (station_landmark_id)
) ENGINE=InnoDB;