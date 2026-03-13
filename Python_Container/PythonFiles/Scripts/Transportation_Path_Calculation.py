import math
import heapq
import SQL_Data_Retriever

VALID_TRANSPORTS = {
    "train",
    "bus",
    "taxi",
    "foot"
}

VALID_OPTIMIZATIONS = {
    "cheapest",
    "fastest",
    "least_transfer"
}

VALID_ALGORITHMS = {
    "astar",
    "greedy",
    "dijkstra"
}

# Speeds in km/hr
SPEEDS_KMH = {
    "train": 60.0,
    "bus": 30.0,
    "taxi": 30.0,
    "foot": 5.0
}


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees).
    """
    R = 6371.0  # Earth radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def _normalize_text(value, field_name):
    if value is None:
        raise ValueError(f"{field_name} is required")

    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} is required")

    return text


def _normalize_transports(transports_available):
    if not isinstance(transports_available, (list, tuple, set)):
        raise ValueError("transports_available must be a list")

    normalized = []
    seen = set()

    for item in transports_available:
        transport = str(item).strip().lower()

        if not transport:
            continue

        if transport not in VALID_TRANSPORTS:
            raise ValueError(
                "Invalid transport '{}'. Allowed values: train, bus, taxi, foot".format(item)
            )

        if transport not in seen:
            seen.add(transport)
            normalized.append(transport)

    if not normalized:
        raise ValueError("At least one transport must be selected")

    return normalized


def _normalize_optimization(element_to_optimize):
    optimization = _normalize_text(element_to_optimize, "element_to_optimize").lower()

    if optimization not in VALID_OPTIMIZATIONS:
        raise ValueError(
            "element_to_optimize must be one of: cheapest, fastest, least_transfer"
        )

    return optimization


def _normalize_algorithm(algorithm_to_use):
    algorithm = _normalize_text(algorithm_to_use, "algorithm_to_use").lower()

    if algorithm not in VALID_ALGORITHMS:
        raise ValueError(
            "algorithm_to_use must be one of: astar, greedy, dijkstra"
        )

    return algorithm


def resolve_landmark(landmarks, lm_ref):
    """
    Helper function to find a landmark dictionary by its ID, name, or abbreviation.
    """
    lm_ref_str = str(lm_ref).strip().lower()
    
    if lm_ref_str.startswith("id:"):
        target_id = lm_ref_str[3:]
        for lm in landmarks:
            if str(lm["landmark_id"]) == target_id:
                return lm
                
    for lm in landmarks:
        if str(lm["landmark_id"]) == lm_ref_str:
            return lm
        if lm["landmark_name"].strip().lower() == lm_ref_str:
            return lm
        if lm.get("abbreviation") and lm["abbreviation"].strip().lower() == lm_ref_str:
            return lm
            
    return None


def _format_segment_output(segment):
    """
    Formats the raw path segment into the final output structure.
    """
    method = segment["transport"].capitalize()
    if segment.get("line_code"):
        method += f" (Line {segment['line_code']})"
        
    return {
        "start_point": segment["start_point"],
        "end_point": segment["end_point"],
        "transportation_method": method,
        "time_minutes": round(segment["time_min"], 2)
    }


def get_best_path(map_id, start_lm, end_lm, transports_available, element_to_optimize, algorithm_to_use):
    if map_id is None:
        raise ValueError("map_id is required")
    
    try:
        map_id = int(map_id)
    except ValueError:
        raise ValueError("map_id must be an integer")

    start_lm = _normalize_text(start_lm, "start_lm")
    end_lm = _normalize_text(end_lm, "end_lm")
    transports_available = _normalize_transports(transports_available)
    element_to_optimize = _normalize_optimization(element_to_optimize)
    algorithm_to_use = _normalize_algorithm(algorithm_to_use)

    # Temporary block for unimplemented features
    if element_to_optimize != "fastest" or algorithm_to_use != "dijkstra":
        return {
            "success": False,
            "error": f"Not implemented yet: algorithm '{algorithm_to_use}' with optimization '{element_to_optimize}'. Please select 'Dijkstra' and 'Fastest'."
        }

    # 1. Fetch map data from the database
    map_data = SQL_Data_Retriever.get_map_preview(map_id)
    if not map_data.get("success"):
        return {
            "success": False, 
            "error": map_data.get("error", "Failed to load map data from database.")
        }
        
    landmarks = map_data.get("landmarks", [])
    start_node = resolve_landmark(landmarks, start_lm)
    end_node = resolve_landmark(landmarks, end_lm)
    
    if not start_node:
        return {"success": False, "error": f"Start landmark '{start_lm}' not found."}
    if not end_node:
        return {"success": False, "error": f"End landmark '{end_lm}' not found."}
        
    if start_node["landmark_id"] == end_node["landmark_id"]:
        return {"success": False, "error": "Start and end landmarks are the same."}

    # 2. Build the graph (Adjacency List)
    graph = {lm["landmark_id"]: [] for lm in landmarks}
    
    def add_edge(u_id, v_id, transport, line_code, time_min):
        graph[u_id].append({
            "to": v_id,
            "transport": transport,
            "line_code": line_code,
            "time_min": time_min
        })

    # Add Bus edges (Bidirectional)
    if "bus" in transports_available:
        for line in map_data.get("bus_lines", []):
            stops = line.get("stops", [])
            for i in range(len(stops) - 1):
                u = stops[i]
                v = stops[i+1]
                dist = haversine(u["latitude"], u["longitude"], v["latitude"], v["longitude"])
                time_min = (dist / SPEEDS_KMH["bus"]) * 60
                add_edge(u["landmark_id"], v["landmark_id"], "bus", line["line_code"], time_min)
                add_edge(v["landmark_id"], u["landmark_id"], "bus", line["line_code"], time_min) # Reverse direction
                
    # Add Train edges (Bidirectional)
    if "train" in transports_available:
        for line in map_data.get("train_lines", []):
            stops = line.get("stops", [])
            for i in range(len(stops) - 1):
                u = stops[i]
                v = stops[i+1]
                dist = haversine(u["latitude"], u["longitude"], v["latitude"], v["longitude"])
                time_min = (dist / SPEEDS_KMH["train"]) * 60
                add_edge(u["landmark_id"], v["landmark_id"], "train", line["line_code"], time_min)
                add_edge(v["landmark_id"], u["landmark_id"], "train", line["line_code"], time_min) # Reverse direction

    # Add Taxi and Foot edges (Complete graph between all landmarks)
    # This covers: Start to all stations, End to all stations, and between all stations.
    for transport in ["taxi", "foot"]:
        if transport in transports_available:
            for i in range(len(landmarks)):
                for j in range(i + 1, len(landmarks)):
                    u = landmarks[i]
                    v = landmarks[j]
                    dist = haversine(u["latitude"], u["longitude"], v["latitude"], v["longitude"])
                    time_min = (dist / SPEEDS_KMH[transport]) * 60
                    
                    add_edge(u["landmark_id"], v["landmark_id"], transport, None, time_min)
                    add_edge(v["landmark_id"], u["landmark_id"], transport, None, time_min)

    # 3. Dijkstra's Algorithm implementation
    pq = [(0.0, start_node["landmark_id"], [])]
    min_time = {start_node["landmark_id"]: 0.0}
    
    best_path = None
    
    while pq:
        curr_time, u_id, path = heapq.heappop(pq)
        
        # If we found a faster way to this node previously, skip
        if curr_time > min_time.get(u_id, float('inf')):
            continue
            
        # Reached destination!
        if u_id == end_node["landmark_id"]:
            best_path = path
            break
            
        # Evaluate all pre-built edges for this node
        for edge in graph[u_id]:
            v_id = edge["to"]
            nxt_time = curr_time + edge["time_min"]
            
            if nxt_time < min_time.get(v_id, float('inf')):
                min_time[v_id] = nxt_time
                segment = {
                    "from": u_id,
                    "to": v_id,
                    "transport": edge["transport"],
                    "line_code": edge["line_code"],
                    "time_min": edge["time_min"]
                }
                heapq.heappush(pq, (nxt_time, v_id, path + [segment]))

    if best_path is None:
        return {
            "success": False,
            "error": "No path found between the selected landmarks."
        }

    # 4. Format the final output path
    formatted_path = []
    total_transfers = 0
    
    if best_path:
        # Create a quick lookup for landmark names to avoid O(N) search every time
        lm_name_map = {lm["landmark_id"]: lm["landmark_name"] for lm in landmarks}
        
        for i, segment in enumerate(best_path):
            seg_data = {
                "start_point": lm_name_map[segment["from"]],
                "end_point": lm_name_map[segment["to"]],
                "transport": segment["transport"],
                "line_code": segment["line_code"],
                "time_min": segment["time_min"]
            }
            formatted_path.append(_format_segment_output(seg_data))
            
            # Count transfers: increment if the transport method or line code changes
            if i > 0:
                prev_seg = best_path[i - 1]
                if prev_seg["transport"] != segment["transport"] or prev_seg["line_code"] != segment["line_code"]:
                    total_transfers += 1

    total_time = sum(seg["time_min"] for seg in best_path)

    return {
        "success": True,
        "message": "Path calculated successfully.",
        "data": {
            "map_id": map_id,
            "start_lm": start_node["landmark_name"],
            "end_lm": end_node["landmark_name"],
            "transports_available": transports_available,
            "element_to_optimize": element_to_optimize,
            "algorithm_to_use": algorithm_to_use,
            "path_found": True,
            "path": formatted_path,
            "summary": {
                "total_cost": None,
                "total_time_minutes": round(total_time, 2),
                "total_transfers": max(0, total_transfers)
            }
        }
    }