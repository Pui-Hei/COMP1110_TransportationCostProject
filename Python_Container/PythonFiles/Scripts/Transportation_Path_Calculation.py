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


def get_best_path(start_lm, end_lm, transports_available, element_to_optimize, algorithm_to_use):
    start_lm = _normalize_text(start_lm, "start_lm")
    end_lm = _normalize_text(end_lm, "end_lm")
    transports_available = _normalize_transports(transports_available)
    element_to_optimize = _normalize_optimization(element_to_optimize)
    algorithm_to_use = _normalize_algorithm(algorithm_to_use)

    return {
        "success": True,
        "message": "Dummy best path calculation only. Real routing is not implemented yet.",
        "data": {
            "start_lm": start_lm,
            "end_lm": end_lm,
            "transports_available": transports_available,
            "element_to_optimize": element_to_optimize,
            "algorithm_to_use": algorithm_to_use,
            "path_found": False,
            "path": [],
            "summary": {
                "total_cost": None,
                "total_time_minutes": None,
                "total_transfers": None
            },
            "note": "This is a placeholder response from TransportationPathCalculation.get_best_path()."
        }
    }