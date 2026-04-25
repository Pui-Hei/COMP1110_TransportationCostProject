const API_BASE_URL = "";
const MAP_PREVIEW_ENDPOINT = (mapId) => `${API_BASE_URL}/maps/${mapId}/preview`;
const BEST_PATH_ENDPOINT = `${API_BASE_URL}/best-path`;

const DEFAULT_CENTER = [22.24, 114.05];
const DEFAULT_ZOOM = 10;

// Updated to highly distinguishable, vibrant color palettes
const BUS_ROUTE_COLORS = [
    "#2563eb", // Blue
    "#9333ea", // Purple
    "#059669", // Emerald
    "#ea580c", // Orange
    "#db2777", // Pink
    "#0d9488", // Teal
    "#4f46e5"  // Indigo
];

const TRAIN_ROUTE_COLORS = [
    "#dc2626", // Red
    "#c026d3", // Fuchsia
    "#0284c7", // Light Blue
    "#65a30d", // Lime
    "#f59e0b", // Amber
    "#be123c", // Rose Dark
    "#b45309"  // Brown/Bronze
];

const LANDMARK_TYPE_COLORS = {
    "Bus Station": "#2563eb",
    "Train Station": "#dc2626",
    "Shopping Mall": "#9333ea",
    "Residential Building": "#6b7280",
    "Recreation Park": "#16a34a"
};

const START_SELECTION_COLOR = "#16a34a";
const END_SELECTION_COLOR = "#e11d48";

const state = {
    leafletMap: null,
    landmarkLayer: null,
    busLayer: null,
    trainLayer: null,
    pathLayer: null, // New layer for the best path
    activeMapId: null,
    activeMapName: "",
    renderedLandmarkMarkers: [],
    selectionMode: "start",
    startSelection: null,
    endSelection: null,
    submittingQuery: false,
    latestRequestId: 0,
    // State for multiple paths
    calculatedPaths: [],
    selectedPathIndex: 0
};

const elements = {
    backButton: null,
    previewTitle: null,
    previewSubtitle: null,
    statusBadge: null,
    landmarkCount: null,
    busLineCount: null,
    trainLineCount: null,
    routeSummary: null,
    mapEmptyState: null,
    queryMap: null,
    selectionHint: null,
    pickStartBtn: null,
    pickEndBtn: null,
    startLandmarkDisplay: null,
    endLandmarkDisplay: null,
    computePathBtn: null,
    queryResultStatus: null,
    queryResultOutput: null,
    // Elements for Beam Search & Path Results
    beamWidthInput: null,
    topKInput: null,
    maxWalkTimeInput: null, // NEW: Max Walk Time Input
    pathResultsContainer: null,
    pathSummariesList: null
};

document.addEventListener("DOMContentLoaded", init);

function init() {
    cacheElements();
    bindEvents();

    try {
        initLeaflet();
    } catch (error) {
        console.error("Leaflet initialization failed:", error);
        setStatus("Leaflet failed", "error");
        elements.previewTitle.textContent = "Leaflet failed to initialize";
        elements.previewSubtitle.textContent = "Check browser console for more details.";
        return;
    }

    updateSelectionModeUI();
    updateSelectionDisplays();
    updateQueryControlsState();
    resetQueryResult();

    loadSelectedMapFromUrl();

    window.addEventListener("resize", () => {
        if (state.leafletMap) {
            setTimeout(() => state.leafletMap.invalidateSize(), 0);
        }
    });
}

function cacheElements() {
    elements.backButton = document.getElementById("backButton");
    elements.previewTitle = document.getElementById("previewTitle");
    elements.previewSubtitle = document.getElementById("previewSubtitle");
    elements.statusBadge = document.getElementById("statusBadge");
    elements.landmarkCount = document.getElementById("landmarkCount");
    elements.busLineCount = document.getElementById("busLineCount");
    elements.trainLineCount = document.getElementById("trainLineCount");
    elements.routeSummary = document.getElementById("routeSummary");
    elements.mapEmptyState = document.getElementById("mapEmptyState");
    elements.queryMap = document.getElementById("queryMap");
    elements.selectionHint = document.getElementById("selectionHint");
    elements.pickStartBtn = document.getElementById("pickStartBtn");
    elements.pickEndBtn = document.getElementById("pickEndBtn");
    elements.startLandmarkDisplay = document.getElementById("startLandmarkDisplay");
    elements.endLandmarkDisplay = document.getElementById("endLandmarkDisplay");
    elements.computePathBtn = document.getElementById("computePathBtn");
    elements.queryResultStatus = document.getElementById("queryResultStatus");
    elements.queryResultOutput = document.getElementById("queryResultOutput");
    
    // Cache new elements
    elements.beamWidthInput = document.getElementById("beamWidthInput");
    elements.topKInput = document.getElementById("topKInput");
    elements.maxWalkTimeInput = document.getElementById("maxWalkTimeInput"); // NEW
    elements.pathResultsContainer = document.getElementById("pathResultsContainer");
    elements.pathSummariesList = document.getElementById("pathSummariesList");
}

function bindEvents() {
    elements.backButton.addEventListener("click", () => {
        window.location.href = "MapPreviewer.html";
    });

    elements.pickStartBtn.addEventListener("click", () => {
        setSelectionMode("start");
    });

    elements.pickEndBtn.addEventListener("click", () => {
        setSelectionMode("end");
    });

    elements.computePathBtn.addEventListener("click", () => {
        submitBestPathQuery();
    });

    document
        .querySelectorAll('input[name="transports_available"], input[name="element_to_optimize"], input[name="algorithm_to_use"]')
        .forEach((input) => {
            input.addEventListener("change", () => {
                updateQueryControlsState();
            });
        });
}

function initLeaflet() {
    state.leafletMap = L.map("queryMap", {
        attributionControl: false,
        zoomControl: true,
        // Set preferCanvas to false so we can use CSS animations on SVG paths
        preferCanvas: false, 
        zoomSnap: 0.25
    });

    state.leafletMap.setView(DEFAULT_CENTER, DEFAULT_ZOOM);

    // Create a custom pane for the path to float above static lines but below markers
    state.leafletMap.createPane('pathPane');
    state.leafletMap.getPane('pathPane').style.zIndex = 550;

    state.busLayer = L.layerGroup().addTo(state.leafletMap);
    state.trainLayer = L.layerGroup().addTo(state.leafletMap);
    state.landmarkLayer = L.layerGroup().addTo(state.leafletMap);
    state.pathLayer = L.layerGroup().addTo(state.leafletMap);
}

function loadSelectedMapFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const rawMapId = params.get("mapId");

    if (!rawMapId) {
        showPageError("Missing mapId in URL. Please open this page from Map Previewer.");
        return;
    }

    const mapId = Number(rawMapId);

    if (!Number.isInteger(mapId) || mapId <= 0) {
        showPageError("Invalid mapId in URL. Please return to Map Previewer and try again.");
        return;
    }

    loadPreview(mapId);
}

async function loadPreview(mapId) {
    state.activeMapId = mapId;
    clearSelections();
    resetQueryResult();
    hideEmptyState();
    setStatus("Loading map...", "loading");
    setPreviewLoadingText(mapId);

    const requestId = ++state.latestRequestId;

    try {
        const result = await fetchJson(MAP_PREVIEW_ENDPOINT(mapId));

        if (requestId !== state.latestRequestId) {
            return;
        }

        if (!result.success) {
            throw new Error(result.error || "Failed to load preview.");
        }

        renderPreview(result);
        setStatus("Map ready", "ready");
    } catch (error) {
        if (requestId !== state.latestRequestId) {
            return;
        }

        console.error("loadPreview failed:", error);
        showPageError(error.message || "Failed to load selected map.");
    }
}

function renderPreview(data) {
    clearMapLayers();

    const mapInfo = data.map || {};
    const landmarks = Array.isArray(data.landmarks) ? data.landmarks : [];
    const busLines = Array.isArray(data.bus_lines) ? data.bus_lines : [];
    const trainLines = Array.isArray(data.train_lines) ? data.train_lines : [];

    state.activeMapName = mapInfo.map_name || "Unnamed Map";

    elements.previewTitle.textContent = state.activeMapName;
    elements.previewSubtitle.textContent = `Map ID: ${mapInfo.map_id ?? "-"} • Click landmarks on the map to choose start and end points.`;

    updateCounts(landmarks.length, busLines.length, trainLines.length);
    updateRouteSummary(busLines, trainLines);

    const boundsPoints = [];

    renderBusLines(busLines, boundsPoints);
    renderTrainLines(trainLines, boundsPoints);
    renderLandmarks(landmarks, boundsPoints);

    fitMapToBounds(boundsPoints);
    hideEmptyState();
    updateSelectionModeUI();
    updateSelectionDisplays();
    updateQueryControlsState();
}

function renderLandmarks(landmarks, boundsPoints) {
    landmarks.forEach((landmark) => {
        const lat = Number(landmark.latitude);
        const lng = Number(landmark.longitude);

        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            return;
        }

        boundsPoints.push([lat, lng]);

        const key = getLandmarkKey(landmark);
        const marker = L.circleMarker([lat, lng], getLandmarkMarkerStyle(landmark, key));

        const tooltipHtml = `
            <div class="tooltip-title">${escapeHtml(landmark.landmark_name || "Unnamed Landmark")}</div>
            <div class="tooltip-subtitle">
                ${escapeHtml(landmark.type || "Unknown Type")}
                ${landmark.abbreviation ? ` (${escapeHtml(landmark.abbreviation)})` : ""}
            </div>
            <div class="tooltip-subtitle">Click to select</div>
        `;

        marker.bindTooltip(tooltipHtml, {
            direction: "top",
            sticky: true,
            className: "landmark-tooltip"
        });

        marker.on("click", () => {
            handleLandmarkClick(landmark);
            marker.openTooltip();
        });

        marker.addTo(state.landmarkLayer);

        state.renderedLandmarkMarkers.push({
            key,
            landmark,
            marker
        });
    });

    updateLandmarkSelectionStyles();
}

function renderBusLines(busLines, boundsPoints) {
    busLines.forEach((line, index) => {
        const stops = Array.isArray(line.stops) ? line.stops : [];
        const latLngs = stops
            .map((stop) => [Number(stop.latitude), Number(stop.longitude)])
            .filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng));

        if (!latLngs.length) {
            return;
        }

        latLngs.forEach((point) => boundsPoints.push(point));

        const color = BUS_ROUTE_COLORS[index % BUS_ROUTE_COLORS.length];

        // Draw white outline background to make the line pop against map tiles
        L.polyline(latLngs, {
            color: '#ffffff',
            weight: 7,
            opacity: 0.8,
            lineCap: "round",
            lineJoin: "round"
        }).addTo(state.busLayer);

        // Draw main colored line
        const polyline = L.polyline(latLngs, {
            color,
            weight: 4,
            opacity: 1.0, // Increased opacity for better visibility
            lineCap: "round",
            lineJoin: "round"
        });

        const tooltipHtml = `
            <div class="tooltip-title">${escapeHtml(line.line_code || "Bus Line")}</div>
            <div class="tooltip-subtitle">
                Bus line • ${stops.length} stop(s)
                ${typeof line.flat_price !== "undefined" ? ` • Flat price: ${escapeHtml(String(line.flat_price))}` : ""}
            </div>
        `;

        polyline.bindTooltip(tooltipHtml, {
            sticky: true,
            className: "route-tooltip"
        });

        polyline.addTo(state.busLayer);
    });
}

function renderTrainLines(trainLines, boundsPoints) {
    trainLines.forEach((line, index) => {
        const stops = Array.isArray(line.stops) ? line.stops : [];
        const latLngs = stops
            .map((stop) => [Number(stop.latitude), Number(stop.longitude)])
            .filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng));

        if (!latLngs.length) {
            return;
        }

        latLngs.forEach((point) => boundsPoints.push(point));

        const color = TRAIN_ROUTE_COLORS[index % TRAIN_ROUTE_COLORS.length];

        // Draw white outline background to make the line pop against map tiles
        L.polyline(latLngs, {
            color: '#ffffff',
            weight: 8,
            opacity: 0.8,
            lineCap: "round",
            lineJoin: "round"
        }).addTo(state.trainLayer);

        // Draw main colored line
        const polyline = L.polyline(latLngs, {
            color,
            weight: 5,
            opacity: 1.0, // Increased opacity for better visibility
            dashArray: "10 8",
            lineCap: "round",
            lineJoin: "round"
        });

        const tooltipHtml = `
            <div class="tooltip-title">${escapeHtml(line.line_code || "Train Line")}</div>
            <div class="tooltip-subtitle">
                Train line • ${stops.length} stop(s)
            </div>
        `;

        polyline.bindTooltip(tooltipHtml, {
            sticky: true,
            className: "route-tooltip"
        });

        polyline.addTo(state.trainLayer);
    });
}

function fitMapToBounds(boundsPoints) {
    if (!state.leafletMap) {
        return;
    }

    if (!boundsPoints.length) {
        state.leafletMap.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
        setTimeout(() => state.leafletMap.invalidateSize(), 0);
        return;
    }

    const bounds = L.latLngBounds(boundsPoints);

    state.leafletMap.fitBounds(bounds, {
        padding: [30, 30],
        maxZoom: 13
    });

    setTimeout(() => state.leafletMap.invalidateSize(), 0);
}

function clearMapLayers() {
    if (state.landmarkLayer) state.landmarkLayer.clearLayers();
    if (state.busLayer) state.busLayer.clearLayers();
    if (state.trainLayer) state.trainLayer.clearLayers();
    if (state.pathLayer) state.pathLayer.clearLayers();

    state.renderedLandmarkMarkers = [];
}

function updateCounts(landmarkCount, busLineCount, trainLineCount) {
    elements.landmarkCount.textContent = String(landmarkCount);
    elements.busLineCount.textContent = String(busLineCount);
    elements.trainLineCount.textContent = String(trainLineCount);
}

function updateRouteSummary(busLines, trainLines) {
    const busCodes = busLines.map((line) => line.line_code).filter(Boolean);
    const trainCodes = trainLines.map((line) => line.line_code).filter(Boolean);

    const busText = busCodes.length
        ? `Bus: ${busCodes.join(", ")}`
        : "Bus: none";

    const trainText = trainCodes.length
        ? `Train: ${trainCodes.join(", ")}`
        : "Train: none";

    elements.routeSummary.textContent = `${busText} | ${trainText}`;
}

function setPreviewLoadingText(mapId) {
    elements.previewTitle.textContent = `Loading map ${mapId}...`;
    elements.previewSubtitle.textContent = "Fetching preview data from the API.";
    elements.routeSummary.textContent = "Loading route information...";
}

function showPageError(message) {
    clearMapLayers();
    updateCounts(0, 0, 0);
    showEmptyState();

    elements.previewTitle.textContent = "Map unavailable";
    elements.previewSubtitle.textContent = message;
    elements.routeSummary.textContent = "Could not load the selected map.";
    setStatus("Load failed", "error");

    clearSelections();
    resetQueryResult();
    updateQueryControlsState();
}

function showEmptyState() {
    elements.mapEmptyState.classList.remove("hidden");
}

function hideEmptyState() {
    elements.mapEmptyState.classList.add("hidden");
}

function setStatus(text, type) {
    elements.statusBadge.textContent = text;
    elements.statusBadge.className = `status-badge ${type}`;
}

function setSelectionMode(mode) {
    state.selectionMode = mode === "end" ? "end" : "start";
    updateSelectionModeUI();
}

function updateSelectionModeUI() {
    elements.pickStartBtn.classList.toggle("active", state.selectionMode === "start");
    elements.pickEndBtn.classList.toggle("active", state.selectionMode === "end");

    if (!state.activeMapId) {
        elements.selectionHint.textContent = "No map loaded.";
        return;
    }

    if (state.selectionMode === "start") {
        elements.selectionHint.textContent = "Click a landmark on the map to choose the start point.";
    } else {
        elements.selectionHint.textContent = "Click a landmark on the map to choose the end point.";
    }
}

function handleLandmarkClick(landmark) {
    const selection = buildLandmarkSelection(landmark);

    if (state.selectionMode === "start") {
        state.startSelection = selection;

        if (state.endSelection && state.endSelection.key === selection.key) {
            state.endSelection = null;
        }

        setSelectionMode("end");
        setStatus("Start selected", "ready");
    } else {
        state.endSelection = selection;

        if (state.startSelection && state.startSelection.key === selection.key) {
            state.startSelection = null;
        }

        setStatus("End selected", "ready");
    }

    updateSelectionDisplays();
    updateLandmarkSelectionStyles();
    updateQueryControlsState();
}

function buildLandmarkSelection(landmark) {
    return {
        key: getLandmarkKey(landmark),
        label: landmark.landmark_name || landmark.abbreviation || "Unnamed Landmark",
        value: getLandmarkRequestValue(landmark),
        type: landmark.type || ""
    };
}

function getLandmarkRequestValue(landmark) {
    if (landmark.landmark_name) {
        return String(landmark.landmark_name);
    }

    if (landmark.abbreviation) {
        return String(landmark.abbreviation);
    }

    if (landmark.landmark_id !== undefined && landmark.landmark_id !== null) {
        return String(landmark.landmark_id);
    }

    if (landmark.id !== undefined && landmark.id !== null) {
        return String(landmark.id);
    }

    return getLandmarkKey(landmark);
}

function getLandmarkKey(landmark) {
    if (landmark.landmark_id !== undefined && landmark.landmark_id !== null && landmark.landmark_id !== "") {
        return `id:${landmark.landmark_id}`;
    }

    if (landmark.id !== undefined && landmark.id !== null && landmark.id !== "") {
        return `id:${landmark.id}`;
    }

    return [
        landmark.landmark_name || landmark.abbreviation || "unnamed",
        landmark.latitude,
        landmark.longitude
    ].join("|");
}

function updateSelectionDisplays() {
    updateSingleSelectionDisplay(
        elements.startLandmarkDisplay,
        state.startSelection,
        "Not selected"
    );

    updateSingleSelectionDisplay(
        elements.endLandmarkDisplay,
        state.endSelection,
        "Not selected"
    );
}

function updateSingleSelectionDisplay(element, selection, emptyText) {
    if (!selection) {
        element.textContent = emptyText;
        element.classList.add("empty");
        return;
    }

    element.textContent = selection.type
        ? `${selection.label} • ${selection.type}`
        : selection.label;

    element.classList.remove("empty");
}

function updateLandmarkSelectionStyles() {
    state.renderedLandmarkMarkers.forEach(({ key, landmark, marker }) => {
        marker.setStyle(getLandmarkMarkerStyle(landmark, key));
    });
}

function getLandmarkMarkerStyle(landmark, key) {
    const isStart = state.startSelection && state.startSelection.key === key;
    const isEnd = state.endSelection && state.endSelection.key === key;

    if (isStart) {
        return {
            radius: 9,
            color: "#ffffff",
            weight: 3,
            fillColor: START_SELECTION_COLOR,
            fillOpacity: 1
        };
    }

    if (isEnd) {
        return {
            radius: 9,
            color: "#ffffff",
            weight: 3,
            fillColor: END_SELECTION_COLOR,
            fillOpacity: 1
        };
    }

    return {
        radius: 6,
        color: "#ffffff",
        weight: 2,
        fillColor: getLandmarkColor(landmark.type),
        fillOpacity: 0.95
    };
}

function clearSelections() {
    state.startSelection = null;
    state.endSelection = null;
    state.selectionMode = "start";

    updateSelectionModeUI();
    updateSelectionDisplays();
    updateLandmarkSelectionStyles();
    updateQueryControlsState();
    if (state.pathLayer) state.pathLayer.clearLayers();
    
    // Clear path results when selections are cleared
    elements.pathResultsContainer.classList.add("hidden");
    elements.pathSummariesList.innerHTML = "";
    state.calculatedPaths = [];
}

function getSelectedTransports() {
    return Array.from(
        document.querySelectorAll('input[name="transports_available"]:checked')
    ).map((input) => input.value);
}

function getSelectedOptimization() {
    const selected = document.querySelector('input[name="element_to_optimize"]:checked');
    return selected ? selected.value : "";
}

function getSelectedAlgorithm() {
    const selected = document.querySelector('input[name="algorithm_to_use"]:checked');
    return selected ? selected.value : "";
}

function updateQueryControlsState() {
    const canSubmit =
        !state.submittingQuery &&
        !!state.activeMapId &&
        !!state.startSelection &&
        !!state.endSelection &&
        getSelectedTransports().length > 0 &&
        state.startSelection.key !== state.endSelection.key;

    elements.computePathBtn.disabled = !canSubmit;
}

async function submitBestPathQuery() {
    if (!state.activeMapId) {
        setQueryResultError("No map loaded.");
        return;
    }

    if (!state.startSelection) {
        setQueryResultError("Please select a start landmark by clicking on the map.");
        return;
    }

    if (!state.endSelection) {
        setQueryResultError("Please select an end landmark by clicking on the map.");
        return;
    }

    if (state.startSelection.key === state.endSelection.key) {
        setQueryResultError("Start and end landmarks must be different.");
        return;
    }

    const transportsAvailable = getSelectedTransports();

    if (!transportsAvailable.length) {
        setQueryResultError("Please choose at least one transport option.");
        return;
    }

    // Include beam_width, top_k, and max_walk_min in payload
    const payload = {
        map_id: state.activeMapId,
        start_lm: state.startSelection.value,
        end_lm: state.endSelection.value,
        transports_available: transportsAvailable,
        element_to_optimize: getSelectedOptimization(),
        algorithm_to_use: getSelectedAlgorithm(),
        beam_width: parseInt(elements.beamWidthInput.value, 10) || 20,
        top_k: parseInt(elements.topKInput.value, 10) || 3,
        max_walk_min: parseFloat(elements.maxWalkTimeInput.value) || 15.0
    };

    state.submittingQuery = true;
    updateQueryControlsState();

    setStatus("Querying path...", "loading");
    setQueryResultStatus("Loading...", "loading");
    elements.queryResultOutput.textContent = `POST ${BEST_PATH_ENDPOINT}\n\n${JSON.stringify(payload, null, 2)}`;
    
    if (state.pathLayer) state.pathLayer.clearLayers();
    elements.pathResultsContainer.classList.add("hidden");

    try {
        const result = await postJson(BEST_PATH_ENDPOINT, payload);

        elements.queryResultOutput.textContent = JSON.stringify(result, null, 2);

        if (result.success) {
            setStatus("Query complete", "ready");
            setQueryResultStatus("Success", "ready");
            
            let pathsToRender = [];

            if (result.data && Array.isArray(result.data.path)) {
                // 1. Push the primary path first
                pathsToRender.push({
                    path: result.data.path,
                    total_cost: result.data.summary.total_cost,
                    total_time: result.data.summary.total_time_minutes,
                    total_transfers: result.data.summary.total_transfers // FIXED: Now pulling actual transfers from API
                });

                // 2. Append the alternative paths generated by the beam search
                if (Array.isArray(result.data.alternative_paths)) {
                    result.data.alternative_paths.forEach(alt => {
                        pathsToRender.push({
                            path: alt.path,
                            total_cost: alt.summary.total_cost,
                            total_time: alt.summary.total_time_minutes,
                            total_transfers: alt.summary.total_transfers // FIXED: Now pulling actual transfers from API
                        });
                    });
                }
            }

            if (pathsToRender.length > 0) {
                state.calculatedPaths = pathsToRender;
                state.selectedPathIndex = 0;
                renderPathSummaries();
                drawPathOnMap(state.calculatedPaths[0].path);
            } else {
                setQueryResultError("No valid path found.");
            }
        } else {
            setStatus("Query failed", "error");
            setQueryResultStatus("Failed", "error");
        }
    } catch (error) {
        console.error("submitBestPathQuery failed:", error);
        setStatus("Query failed", "error");
        setQueryResultStatus("Failed", "error");
        elements.queryResultOutput.textContent = error.message;
    } finally {
        state.submittingQuery = false;
        updateQueryControlsState();
    }
}

// Function to render the list of alternative paths
function renderPathSummaries() {
    elements.pathSummariesList.innerHTML = "";
    
    if (state.calculatedPaths.length === 0) {
        elements.pathResultsContainer.classList.add("hidden");
        return;
    }

    elements.pathResultsContainer.classList.remove("hidden");

    state.calculatedPaths.forEach((pathData, index) => {
        const card = document.createElement("div");
        card.className = `path-card ${index === state.selectedPathIndex ? "selected" : ""}`;
        
        const cost = pathData.total_cost !== undefined ? `$${pathData.total_cost}` : "N/A";
        const time = pathData.total_time !== undefined ? `${pathData.total_time} min` : "N/A";
        // FIXED: Use the exact transfer count returned by the API instead of calculating it from steps
        const transfers = pathData.total_transfers !== undefined ? pathData.total_transfers : "N/A";
        const steps = Array.isArray(pathData.path) ? pathData.path.length : 0;

        card.innerHTML = `
            <div class="path-card-title">
                <span>Path Option ${index + 1}</span>
                ${index === 0 ? '<span class="rank-badge">Best</span>' : ''}
            </div>
            <div class="path-card-stats">
                <span>Cost: ${cost}</span>
                <span>Time: ${time}</span>
                <span>Transfers: ${transfers}</span>
                <span>Steps: ${steps}</span>
            </div>
        `;

        card.addEventListener("click", () => {
            state.selectedPathIndex = index;
            // Update UI selection
            Array.from(elements.pathSummariesList.children).forEach((c, i) => {
                c.classList.toggle("selected", i === index);
            });
            // Draw the selected path
            drawPathOnMap(state.calculatedPaths[index].path);
        });

        elements.pathSummariesList.appendChild(card);
    });
}

function drawPathOnMap(pathSegments) {
    if (state.pathLayer) state.pathLayer.clearLayers();
    if (!pathSegments || !pathSegments.length) return;

    const pathBounds = [];

    pathSegments.forEach((segment, index) => {
        // Find the coordinates for the start and end landmarks of this segment
        const startObj = state.renderedLandmarkMarkers.find(m => m.landmark.landmark_name === segment.start_point);
        const endObj = state.renderedLandmarkMarkers.find(m => m.landmark.landmark_name === segment.end_point);

        if (!startObj || !endObj) return;

        const startLatLng = [Number(startObj.landmark.latitude), Number(startObj.landmark.longitude)];
        const endLatLng = [Number(endObj.landmark.latitude), Number(endObj.landmark.longitude)];

        pathBounds.push(startLatLng, endLatLng);

        // Determine line color based on transport method
        let color = "#16a34a"; // Default to foot (green)
        const method = (segment.transportation_method || "").toLowerCase();
        
        if (method.includes("train")) color = "#e11d48"; // Rose
        else if (method.includes("bus")) color = "#2563eb"; // Blue
        else if (method.includes("taxi")) color = "#d97706"; // Amber

        // Draw a thick white background line to create a "glow" and ensure visibility over other map lines
        L.polyline([startLatLng, endLatLng], {
            color: '#ffffff',
            weight: 8,
            opacity: 0.9,
            pane: 'pathPane',
            lineCap: 'round',
            lineJoin: 'round'
        }).addTo(state.pathLayer);

        // Draw the main animated dashed line
        const polyline = L.polyline([startLatLng, endLatLng], {
            color: color,
            weight: 5,
            opacity: 1,
            pane: 'pathPane',
            className: 'animated-path', // Hooks into the CSS animation
            lineCap: 'round',
            lineJoin: 'round'
        });

        const tooltipHtml = `
            <div class="tooltip-title">Step ${index + 1}: ${escapeHtml(segment.transportation_method)}</div>
            <div class="tooltip-subtitle">${escapeHtml(segment.start_point)} ➔ ${escapeHtml(segment.end_point)}</div>
            <div class="tooltip-subtitle">Time: ${segment.time_minutes} min</div>
        `;

        polyline.bindTooltip(tooltipHtml, {
            sticky: true,
            className: 'route-tooltip'
        });

        polyline.addTo(state.pathLayer);
    });

    // Zoom and pan the map to comfortably fit the calculated path
    if (pathBounds.length > 0) {
        state.leafletMap.fitBounds(L.latLngBounds(pathBounds), {
            padding: [50, 50],
            maxZoom: 13
        });
    }
}

function resetQueryResult() {
    setQueryResultStatus("Waiting...", "idle");
    elements.queryResultOutput.textContent = "No path query has been sent yet.";
    if (state.pathLayer) state.pathLayer.clearLayers();
    
    // Clear path results on reset
    if (elements.pathResultsContainer) {
        elements.pathResultsContainer.classList.add("hidden");
        elements.pathSummariesList.innerHTML = "";
    }
    state.calculatedPaths = [];
}

function setQueryResultError(message) {
    setStatus("Invalid query", "error");
    setQueryResultStatus("Error", "error");
    elements.queryResultOutput.textContent = message;
}

function setQueryResultStatus(text, type) {
    elements.queryResultStatus.textContent = text;
    elements.queryResultStatus.className = `result-status ${type}`;
}

function getLandmarkColor(type) {
    return LANDMARK_TYPE_COLORS[type] || "#334155";
}

async function fetchJson(url) {
    const response = await fetch(url, {
        method: "GET",
        headers: {
            "Accept": "application/json"
        }
    });

    const text = await response.text();

    let data;
    try {
        data = JSON.parse(text);
    } catch (error) {
        throw new Error(`Non-JSON response from ${url}`);
    }

    if (!response.ok) {
        throw new Error(data.error || `Request failed with status ${response.status}`);
    }

    return data;
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const text = await response.text();

    let data;
    try {
        data = JSON.parse(text);
    } catch (error) {
        throw new Error(`Non-JSON response from ${url}`);
    }

    if (!response.ok) {
        throw new Error(data.error || `Request failed with status ${response.status}`);
    }

    return data;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}