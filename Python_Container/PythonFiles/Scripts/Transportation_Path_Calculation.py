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

TAXI_RATE_PER_KM = 12.0
DEFAULT_TOP_K_PATHS = 3
DEFAULT_BEAM_WIDTH = 20
EPSILON = 1e-9


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


def _normalize_beam_width(beam_width):
    if beam_width in (None, ""):
        return DEFAULT_BEAM_WIDTH

    try:
        width = int(beam_width)
    except (TypeError, ValueError):
        raise ValueError("beam_width must be a positive integer")

    if width <= 0:
        raise ValueError("beam_width must be a positive integer")

    return width


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


def _build_graph_and_lookups(map_data, transports_available):
    landmarks = map_data.get("landmarks", [])
    graph = {lm["landmark_id"]: [] for lm in landmarks}

    landmark_lookup = {lm["landmark_id"]: lm for lm in landmarks}
    bus_price_lookup = {}
    train_fee_lookup = {}

    def add_edge(u_id, v_id, transport, line_code, time_min, distance_km):
        graph[u_id].append({
            "from": u_id,
            "to": v_id,
            "transport": transport,
            "line_code": line_code,
            "time_min": time_min,
            "distance_km": distance_km
        })

    if "bus" in transports_available:
        for line in map_data.get("bus_lines", []):
            line_code = line.get("line_code")
            if line_code is not None:
                bus_price_lookup[line_code] = float(line.get("flat_price") or 0.0)

            stops = line.get("stops", [])
            for i in range(len(stops) - 1):
                u = stops[i]
                v = stops[i + 1]
                distance_km = haversine(u["latitude"], u["longitude"], v["latitude"], v["longitude"])
                time_min = (distance_km / SPEEDS_KMH["bus"]) * 60

                add_edge(u["landmark_id"], v["landmark_id"], "bus", line_code, time_min, distance_km)
                add_edge(v["landmark_id"], u["landmark_id"], "bus", line_code, time_min, distance_km)

    if "train" in transports_available:
        for line in map_data.get("train_lines", []):
            line_code = line.get("line_code")

            for fee in line.get("fees", []):
                from_station = fee.get("from_station_landmark_id")
                to_station = fee.get("to_station_landmark_id")
                if from_station is None or to_station is None or line_code is None:
                    continue

                train_fee_lookup[(line_code, from_station, to_station)] = float(fee.get("price") or 0.0)

            stops = line.get("stops", [])
            for i in range(len(stops) - 1):
                u = stops[i]
                v = stops[i + 1]
                distance_km = haversine(u["latitude"], u["longitude"], v["latitude"], v["longitude"])
                time_min = (distance_km / SPEEDS_KMH["train"]) * 60

                add_edge(u["landmark_id"], v["landmark_id"], "train", line_code, time_min, distance_km)
                add_edge(v["landmark_id"], u["landmark_id"], "train", line_code, time_min, distance_km)

    for transport in ["taxi", "foot"]:
        if transport in transports_available:
            for i in range(len(landmarks)):
                for j in range(i + 1, len(landmarks)):
                    u = landmarks[i]
                    v = landmarks[j]
                    distance_km = haversine(u["latitude"], u["longitude"], v["latitude"], v["longitude"])
                    time_min = (distance_km / SPEEDS_KMH[transport]) * 60

                    add_edge(u["landmark_id"], v["landmark_id"], transport, None, time_min, distance_km)
                    add_edge(v["landmark_id"], u["landmark_id"], transport, None, time_min, distance_km)

    return graph, landmark_lookup, bus_price_lookup, train_fee_lookup


def _make_initial_state(start_node_id):
    return {
        "node_id": start_node_id,
        "path_segments": [],
        "node_sequence": (start_node_id,),
        "total_time": 0.0,
        "total_cost": 0.0,
        "total_transfers": 0,
        "foot_minutes": 0.0,
        "last_transport": None,
        "last_line": None,
        "objective_score": 0.0
    }


def _calculate_transfer_delta(prev_transport, prev_line, next_transport, next_line):
    if prev_transport is None:
        return 0

    if prev_transport != next_transport:
        return 1

    if prev_line != next_line:
        return 1

    return 0


def _edge_cost(edge, state, bus_price_lookup, train_fee_lookup):
    transport = edge["transport"]

    if transport == "foot":
        return 0.0

    if transport == "taxi":
        return edge["distance_km"] * TAXI_RATE_PER_KM

    if transport == "bus":
        if state["last_transport"] == "bus" and state["last_line"] == edge["line_code"]:
            return 0.0
        return float(bus_price_lookup.get(edge["line_code"], 0.0))

    if transport == "train":
        key = (edge["line_code"], edge["from"], edge["to"])
        reverse_key = (edge["line_code"], edge["to"], edge["from"])

        if key in train_fee_lookup:
            return train_fee_lookup[key]

        if reverse_key in train_fee_lookup:
            return train_fee_lookup[reverse_key]

        return None

    return 0.0


def _score_state(state, optimization):
    if optimization == "fastest":
        return state["total_time"]
    if optimization == "cheapest":
        return state["total_cost"]
    if optimization == "least_transfer":
        return float(state["total_transfers"])
    return float("inf")


def _state_signature(state):
    foot_bucket = int(round(state["foot_minutes"] * 100))
    return (state["node_id"], state["last_transport"], state["last_line"], foot_bucket)


def _path_identity(state):
    return tuple(
        (seg["from"], seg["to"], seg["transport"], seg["line_code"])
        for seg in state["path_segments"]
    )


def _advance_state(state, edge, optimization, bus_price_lookup, train_fee_lookup, max_walk_min):
    if edge["to"] in state["node_sequence"]:
        return None

    next_foot_minutes = state["foot_minutes"]
    if edge["transport"] == "foot":
        next_foot_minutes += edge["time_min"]
        if next_foot_minutes > max_walk_min + EPSILON:
            return None

    transfer_delta = _calculate_transfer_delta(
        state["last_transport"],
        state["last_line"],
        edge["transport"],
        edge["line_code"]
    )

    edge_cost = _edge_cost(edge, state, bus_price_lookup, train_fee_lookup)
    if edge_cost is None:
        if optimization == "cheapest":
            return None
        edge_cost = 0.0

    new_segment = {
        "from": edge["from"],
        "to": edge["to"],
        "transport": edge["transport"],
        "line_code": edge["line_code"],
        "time_min": edge["time_min"],
        "distance_km": edge["distance_km"],
        "cost": edge_cost
    }

    new_state = {
        "node_id": edge["to"],
        "path_segments": state["path_segments"] + [new_segment],
        "node_sequence": state["node_sequence"] + (edge["to"],),
        "total_time": state["total_time"] + edge["time_min"],
        "total_cost": state["total_cost"] + edge_cost,
        "total_transfers": state["total_transfers"] + transfer_delta,
        "foot_minutes": next_foot_minutes,
        "last_transport": edge["transport"],
        "last_line": edge["line_code"],
        "objective_score": 0.0
    }

    new_state["objective_score"] = _score_state(new_state, optimization)
    return new_state


def _heuristic_minutes(node_id, end_node_id, landmark_lookup, transports_available):
    current = landmark_lookup[node_id]
    goal = landmark_lookup[end_node_id]

    distance_km = haversine(
        current["latitude"],
        current["longitude"],
        goal["latitude"],
        goal["longitude"]
    )

    max_speed = max(SPEEDS_KMH[t] for t in transports_available)
    return (distance_km / max_speed) * 60


def _heuristic_objective_lower_bound(
    node_id,
    end_node_id,
    optimization,
    transports_available,
    landmark_lookup
):
    if node_id == end_node_id:
        return 0.0

    if optimization == "fastest":
        return _heuristic_minutes(node_id, end_node_id, landmark_lookup, transports_available)

    # For cheapest and least_transfer, a conservative admissible lower bound is 0.
    return 0.0


def _astar_priority(state, end_node_id, optimization, transports_available, landmark_lookup):
    return state["objective_score"] + _heuristic_objective_lower_bound(
        state["node_id"],
        end_node_id,
        optimization,
        transports_available,
        landmark_lookup
    )


def _run_dijkstra(
    graph,
    start_node_id,
    end_node_id,
    optimization,
    bus_price_lookup,
    train_fee_lookup,
    max_walk_min
):
    start_state = _make_initial_state(start_node_id)
    start_state["objective_score"] = _score_state(start_state, optimization)

    state_counter = 0
    pq = [(start_state["objective_score"], state_counter, start_state)]
    best_score_by_signature = {_state_signature(start_state): start_state["objective_score"]}

    while pq:
        _, _, state = heapq.heappop(pq)
        signature = _state_signature(state)
        best_score = best_score_by_signature.get(signature, float("inf"))

        if state["objective_score"] > best_score + EPSILON:
            continue

        if state["node_id"] == end_node_id:
            return state

        for edge in graph[state["node_id"]]:
            next_state = _advance_state(
                state,
                edge,
                optimization,
                bus_price_lookup,
                train_fee_lookup,
                max_walk_min
            )

            if next_state is None:
                continue

            next_signature = _state_signature(next_state)
            next_best_score = best_score_by_signature.get(next_signature, float("inf"))

            if next_state["objective_score"] + EPSILON < next_best_score:
                best_score_by_signature[next_signature] = next_state["objective_score"]
                state_counter += 1
                heapq.heappush(
                    pq,
                    (next_state["objective_score"], state_counter, next_state)
                )

    return None


def _run_astar(
    graph,
    start_node_id,
    end_node_id,
    optimization,
    transports_available,
    landmark_lookup,
    bus_price_lookup,
    train_fee_lookup
):
    start_state = _make_initial_state(start_node_id)
    start_state["objective_score"] = _score_state(start_state, optimization)

    state_counter = 0
    pq = [(
        _astar_priority(start_state, end_node_id, optimization, transports_available, landmark_lookup),
        start_state["objective_score"],
        state_counter,
        start_state
    )]
    best_score_by_signature = {_state_signature(start_state): start_state["objective_score"]}

    while pq:
        _, _, _, state = heapq.heappop(pq)
        signature = _state_signature(state)
        best_score = best_score_by_signature.get(signature, float("inf"))

        if state["objective_score"] > best_score + EPSILON:
            continue

        if state["node_id"] == end_node_id:
            return state

        for edge in graph[state["node_id"]]:
            next_state = _advance_state(
                state,
                edge,
                optimization,
                bus_price_lookup,
                train_fee_lookup
            )

            if next_state is None:
                continue

            next_signature = _state_signature(next_state)
            next_best_score = best_score_by_signature.get(next_signature, float("inf"))

            if next_state["objective_score"] + EPSILON < next_best_score:
                best_score_by_signature[next_signature] = next_state["objective_score"]
                state_counter += 1
                heapq.heappush(
                    pq,
                    (
                        _astar_priority(
                            next_state,
                            end_node_id,
                            optimization,
                            transports_available,
                            landmark_lookup
                        ),
                        next_state["objective_score"],
                        state_counter,
                        next_state
                    )
                )

    return None


def _run_greedy(
    graph,
    start_node_id,
    end_node_id,
    optimization,
    transports_available,
    landmark_lookup,
    bus_price_lookup,
    train_fee_lookup,
    max_walk_min
):
    start_state = _make_initial_state(start_node_id)
    start_state["objective_score"] = _score_state(start_state, optimization)

    state_counter = 0
    start_heuristic = _heuristic_minutes(start_node_id, end_node_id, landmark_lookup, transports_available)
    pq = [(start_heuristic, 0.0, state_counter, start_state)]
    best_score_by_signature = {_state_signature(start_state): start_state["objective_score"]}

    while pq:
        _, _, _, state = heapq.heappop(pq)

        if state["node_id"] == end_node_id:
            return state

        for edge in graph[state["node_id"]]:
            next_state = _advance_state(
                state,
                edge,
                optimization,
                bus_price_lookup,
                train_fee_lookup,
                max_walk_min
            )

            if next_state is None:
                continue

            next_signature = _state_signature(next_state)
            next_best_score = best_score_by_signature.get(next_signature, float("inf"))

            if next_state["objective_score"] + EPSILON < next_best_score:
                best_score_by_signature[next_signature] = next_state["objective_score"]
                heuristic = _heuristic_minutes(
                    next_state["node_id"],
                    end_node_id,
                    landmark_lookup,
                    transports_available
                )
                state_counter += 1
                heapq.heappush(
                    pq,
                    (heuristic, next_state["objective_score"], state_counter, next_state)
                )

    return None


def _objective_sort_key(state, optimization):
    if optimization == "fastest":
        return state["total_time"]
    if optimization == "cheapest":
        return state["total_cost"]
    return float(state["total_transfers"])


def _beam_ranked_paths(
    graph,
    start_node_id,
    end_node_id,
    optimization,
    beam_width,
    top_k,
    strategy,
    transports_available,
    landmark_lookup,
    bus_price_lookup,
    train_fee_lookup,
    max_walk_min
):
    start_state = _make_initial_state(start_node_id)
    start_state["objective_score"] = _score_state(start_state, optimization)

    frontier = [start_state]
    complete_paths = []
    seen_path_identities = set()
    best_score_by_signature = {_state_signature(start_state): start_state["objective_score"]}

    max_steps = max(50, len(graph) * 5)

    for _ in range(max_steps):
        if not frontier:
            break

        next_frontier = []

        for state in frontier:
            if state["node_id"] == end_node_id:
                identity = _path_identity(state)
                if identity not in seen_path_identities:
                    seen_path_identities.add(identity)
                    complete_paths.append(state)
                continue

            for edge in graph[state["node_id"]]:
                next_state = _advance_state(
                    state,
                    edge,
                    optimization,
                    bus_price_lookup,
                    train_fee_lookup,
                    max_walk_min
                )

                if next_state is None:
                    continue

                next_signature = _state_signature(next_state)
                next_best_score = best_score_by_signature.get(next_signature, float("inf"))

                if next_state["objective_score"] + EPSILON < next_best_score:
                    best_score_by_signature[next_signature] = next_state["objective_score"]
                    next_frontier.append(next_state)

        if not next_frontier:
            if len(complete_paths) >= top_k:
                break
            continue

        if strategy == "greedy":
            next_frontier.sort(
                key=lambda st: (
                    _heuristic_minutes(st["node_id"], end_node_id, landmark_lookup, transports_available),
                    _objective_sort_key(st, optimization)
                )
            )
        elif strategy == "astar":
            next_frontier.sort(
                key=lambda st: (
                    _astar_priority(st, end_node_id, optimization, transports_available, landmark_lookup),
                    _objective_sort_key(st, optimization)
                )
            )
        else:
            next_frontier.sort(key=lambda st: _objective_sort_key(st, optimization))

        frontier = next_frontier[:beam_width]

    for state in frontier:
        if state["node_id"] == end_node_id:
            identity = _path_identity(state)
            if identity not in seen_path_identities:
                seen_path_identities.add(identity)
                complete_paths.append(state)

    complete_paths.sort(key=lambda st: _objective_sort_key(st, optimization))
    return complete_paths[:top_k]


def _format_state_path(state, landmark_lookup):
    formatted = []

    for segment in state["path_segments"]:
        from_lm = landmark_lookup[segment["from"]]
        to_lm = landmark_lookup[segment["to"]]

        seg_data = {
            "start_point": from_lm["landmark_name"],
            "end_point": to_lm["landmark_name"],
            "transport": segment["transport"],
            "line_code": segment["line_code"],
            "time_min": segment["time_min"]
        }
        formatted.append(_format_segment_output(seg_data))

    return formatted


def _state_summary(state):
    return {
        "total_cost": round(state["total_cost"], 2),
        "total_time_minutes": round(state["total_time"], 2),
        "total_transfers": max(0, int(state["total_transfers"])),
        "foot_minutes_used": round(state["foot_minutes"], 2)
    }

def _build_alternative_outputs(primary_state, ranked_states, landmark_lookup, top_k):
    alternatives = []
    primary_identity = _path_identity(primary_state)

    for state in ranked_states:
        if _path_identity(state) == primary_identity:
            continue

        alternatives.append({
            "rank": len(alternatives) + 2,
            "path": _format_state_path(state, landmark_lookup),
            "summary": _state_summary(state)
        })

        # Use the dynamic top_k here
        if len(alternatives) >= max(0, top_k - 1):
            break

    return alternatives


def get_best_path(
    map_id,
    start_lm,
    end_lm,
    transports_available,
    element_to_optimize,
    algorithm_to_use,
    beam_width=None,
    top_k=None,
    max_walk_min=15.0
):
    if map_id is None:
        raise ValueError("map_id is required")
    
    try:
        map_id = int(map_id)
    except ValueError:
        raise ValueError("map_id must be an integer")
    if top_k is None:
        top_k = DEFAULT_TOP_K_PATHS
    else:
        top_k = int(top_k)
    start_lm = _normalize_text(start_lm, "start_lm")
    end_lm = _normalize_text(end_lm, "end_lm")
    transports_available = _normalize_transports(transports_available)
    element_to_optimize = _normalize_optimization(element_to_optimize)
    algorithm_to_use = _normalize_algorithm(algorithm_to_use)
    beam_width = _normalize_beam_width(beam_width)

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

    graph, landmark_lookup, bus_price_lookup, train_fee_lookup = _build_graph_and_lookups(
        map_data,
        transports_available
    )

    start_id = start_node["landmark_id"]
    end_id = end_node["landmark_id"]

    if algorithm_to_use == "dijkstra":
        best_state = _run_dijkstra(
            graph,
            start_id,
            end_id,
            element_to_optimize,
            bus_price_lookup,
            train_fee_lookup,
            max_walk_min
        )
    elif algorithm_to_use == "astar":
        best_state = _run_astar(
            graph,
            start_id,
            end_id,
            element_to_optimize,
            transports_available,
            landmark_lookup,
            bus_price_lookup,
            train_fee_lookup
        )
    elif algorithm_to_use == "greedy":
        best_state = _run_greedy(
            graph,
            start_id,
            end_id,
            element_to_optimize,
            transports_available,
            landmark_lookup,
            bus_price_lookup,
            train_fee_lookup,
            max_walk_min
        )
    else:
        return {
            "success": False,
            "error": f"Algorithm '{algorithm_to_use}' is not supported in this branch."
        }

    if best_state is None:
        return {
            "success": False,
            "error": "No path found between the selected landmarks."
        }

    ranked_states = _beam_ranked_paths(
        graph=graph,
        start_node_id=start_id,
        end_node_id=end_id,
        optimization=element_to_optimize,
        beam_width=beam_width,
        top_k=top_k,
        strategy=algorithm_to_use,
        transports_available=transports_available,
        landmark_lookup=landmark_lookup,
        bus_price_lookup=bus_price_lookup,
        train_fee_lookup=train_fee_lookup,
        max_walk_min=max_walk_min
    )

    formatted_path = _format_state_path(best_state, landmark_lookup)
    summary = _state_summary(best_state)
    alternative_outputs = _build_alternative_outputs(
        best_state,
        ranked_states,
        landmark_lookup,
        top_k
    )

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
            "alternative_paths": alternative_outputs,
            "summary": summary
        }
    }