const API_BASE_URL = "";
const MAPS_ENDPOINT = "/maps";
const MAP_PREVIEW_ENDPOINT = (mapId) => `/maps/${mapId}/preview`;

const DEFAULT_CENTER = [22.24, 114.05];
const DEFAULT_ZOOM = 10;
const HOVER_DELAY_MS = 180;

const BUS_ROUTE_COLORS = ["#2563eb", "#0ea5e9", "#0284c7", "#06b6d4", "#1d4ed8"];
const TRAIN_ROUTE_COLORS = ["#dc2626", "#f97316", "#e11d48", "#b91c1c", "#ef4444"];

const LANDMARK_TYPE_COLORS = {
    "Bus Station": "#2563eb",
    "Train Station": "#dc2626",
    "Shopping Mall": "#9333ea",
    "Residential Building": "#6b7280",
    "Recreation Park": "#16a34a"
};

const state = {
    leafletMap: null,
    landmarkLayer: null,
    busLayer: null,
    trainLayer: null,
    previewCache: new Map(),
    hoverTimer: null,
    activeMapId: null,
    latestRequestId: 0
};

const elements = {
    mapsList: null,
    previewTitle: null,
    previewSubtitle: null,
    statusBadge: null,
    landmarkCount: null,
    busLineCount: null,
    trainLineCount: null,
    routeSummary: null,
    mapEmptyState: null,
    previewMap: null
};

document.addEventListener("DOMContentLoaded", init);

function init() {
    cacheElements();

    console.log("MapPreviewer init started");
    console.log("Leaflet available:", typeof L !== "undefined");

    try {
        initLeaflet();
    } catch (error) {
        console.error("Leaflet initialization failed:", error);
        setStatus("Leaflet failed", "error");
        elements.previewTitle.textContent = "Leaflet failed to initialize";
        elements.previewSubtitle.textContent = "Map list can still load. Check browser console.";
    }

    loadMaps();

    window.addEventListener("resize", () => {
        if (state.leafletMap) {
            setTimeout(() => state.leafletMap.invalidateSize(), 0);
        }
    });
}

function cacheElements() {
    elements.mapsList = document.getElementById("mapsList");
    elements.previewTitle = document.getElementById("previewTitle");
    elements.previewSubtitle = document.getElementById("previewSubtitle");
    elements.statusBadge = document.getElementById("statusBadge");
    elements.landmarkCount = document.getElementById("landmarkCount");
    elements.busLineCount = document.getElementById("busLineCount");
    elements.trainLineCount = document.getElementById("trainLineCount");
    elements.routeSummary = document.getElementById("routeSummary");
    elements.mapEmptyState = document.getElementById("mapEmptyState");
    elements.previewMap = document.getElementById("previewMap");
}

function initLeaflet() {
    state.leafletMap = L.map("previewMap", {
        attributionControl: false,
        zoomControl: true,
        preferCanvas: true,
        zoomSnap: 0.25
    });

    state.leafletMap.setView(DEFAULT_CENTER, DEFAULT_ZOOM);

    state.busLayer = L.layerGroup().addTo(state.leafletMap);
    state.trainLayer = L.layerGroup().addTo(state.leafletMap);
    state.landmarkLayer = L.layerGroup().addTo(state.leafletMap);
}

async function loadMaps() {
    console.log("Loading maps from:", MAPS_ENDPOINT);

    setStatus("Loading maps...", "loading");
    elements.mapsList.innerHTML = '<div class="list-state">Loading maps...</div>';

    try {
        const result = await fetchJson(MAPS_ENDPOINT);
        console.log("Maps response:", result);

        const maps = Array.isArray(result)
            ? result
            : Array.isArray(result.maps)
                ? result.maps
                : null;

        if (!maps) {
            throw new Error("Invalid response while loading maps.");
        }

        renderMapsList(maps);
        setStatus("Ready", "ready");

        if (maps.length === 0) {
            setStatus("No maps", "idle");
        }
    } catch (error) {
        console.error("loadMaps failed:", error);

        elements.mapsList.innerHTML = `
            <div class="list-state">
                Failed to load maps.<br />
                ${escapeHtml(error.message)}
            </div>
        `;
        setStatus("Load failed", "error");
    }
}

function renderMapsList(maps) {
    if (!maps.length) {
        elements.mapsList.innerHTML = '<div class="list-state">No maps available.</div>';
        return;
    }

    const fragment = document.createDocumentFragment();

    maps.forEach((mapItem) => {
        const link = document.createElement("a");
        const targetUrl = new URL("MapPathQuery.html", window.location.href);
        targetUrl.searchParams.set("mapId", String(mapItem.map_id));

        link.className = "map-button";
        link.dataset.mapId = String(mapItem.map_id);
        link.href = targetUrl.toString();

        link.innerHTML = `
            <span class="map-button-name">${escapeHtml(mapItem.map_name || "Unnamed Map")}</span>
            <span class="map-button-meta">Map ID: ${escapeHtml(String(mapItem.map_id))}</span>
        `;

        link.addEventListener("mouseenter", () => {
            schedulePreview(mapItem.map_id);
        });

        link.addEventListener("focus", () => {
            schedulePreview(mapItem.map_id);
        });

        link.addEventListener("click", () => {
            clearHoverTimer();
            console.log("Navigating to:", targetUrl.toString());
        });

        fragment.appendChild(link);
    });

    elements.mapsList.innerHTML = "";
    elements.mapsList.appendChild(fragment);
}
function schedulePreview(mapId) {
    clearHoverTimer();
    state.hoverTimer = window.setTimeout(() => {
        loadPreview(mapId);
    }, HOVER_DELAY_MS);
}

function clearHoverTimer() {
    if (state.hoverTimer) {
        window.clearTimeout(state.hoverTimer);
        state.hoverTimer = null;
    }
}

async function loadPreview(mapId) {
    state.activeMapId = mapId;
    highlightActiveMapButton(mapId);
    hideEmptyState();
    setStatus("Loading preview...", "loading");
    setPreviewLoadingText(mapId);

    if (state.previewCache.has(mapId)) {
        const cachedPreview = state.previewCache.get(mapId);
        renderPreview(cachedPreview);
        setStatus("Preview ready", "ready");
        return;
    }

    const requestId = ++state.latestRequestId;

    try {
        const result = await fetchJson(MAP_PREVIEW_ENDPOINT(mapId));

        if (requestId !== state.latestRequestId) {
            return;
        }

        if (!result.success) {
            throw new Error(result.error || "Failed to load preview.");
        }

        state.previewCache.set(mapId, result);
        renderPreview(result);
        setStatus("Preview ready", "ready");
    } catch (error) {
        if (requestId !== state.latestRequestId) {
            return;
        }

        clearMapLayers();
        showEmptyState();
        elements.previewTitle.textContent = "Preview failed";
        elements.previewSubtitle.textContent = error.message;
        elements.routeSummary.textContent = "Could not render this map preview.";
        updateCounts(0, 0, 0);
        setStatus("Preview failed", "error");
    }
}

function renderPreview(data) {
    clearMapLayers();

    const mapInfo = data.map || {};
    const landmarks = Array.isArray(data.landmarks) ? data.landmarks : [];
    const busLines = Array.isArray(data.bus_lines) ? data.bus_lines : [];
    const trainLines = Array.isArray(data.train_lines) ? data.train_lines : [];

    elements.previewTitle.textContent = mapInfo.map_name || "Unnamed Map";
    elements.previewSubtitle.textContent = `Map ID: ${mapInfo.map_id ?? "-"} • Hover another map on the left to switch preview.`;

    updateCounts(landmarks.length, busLines.length, trainLines.length);
    updateRouteSummary(busLines, trainLines);

    const boundsPoints = [];

    renderBusLines(busLines, boundsPoints);
    renderTrainLines(trainLines, boundsPoints);
    renderLandmarks(landmarks, boundsPoints);

    fitMapToBounds(boundsPoints);

    hideEmptyState();
}

function renderLandmarks(landmarks, boundsPoints) {
    landmarks.forEach((landmark) => {
        const lat = Number(landmark.latitude);
        const lng = Number(landmark.longitude);

        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            return;
        }

        boundsPoints.push([lat, lng]);

        const color = getLandmarkColor(landmark.type);

        const marker = L.circleMarker([lat, lng], {
            radius: 6,
            color: "#ffffff",
            weight: 2,
            fillColor: color,
            fillOpacity: 0.95
        });

        const tooltipHtml = `
            <div class="tooltip-title">${escapeHtml(landmark.landmark_name || "Unnamed Landmark")}</div>
            <div class="tooltip-subtitle">
                ${escapeHtml(landmark.type || "Unknown Type")}
                ${landmark.abbreviation ? ` (${escapeHtml(landmark.abbreviation)})` : ""}
            </div>
        `;

        marker.bindTooltip(tooltipHtml, {
            direction: "top",
            sticky: true,
            className: "landmark-tooltip"
        });

        marker.addTo(state.landmarkLayer);
    });
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

        const polyline = L.polyline(latLngs, {
            color,
            weight: 4,
            opacity: 0.85,
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

        const polyline = L.polyline(latLngs, {
            color,
            weight: 5,
            opacity: 0.9,
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
    state.landmarkLayer.clearLayers();
    state.busLayer.clearLayers();
    state.trainLayer.clearLayers();
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

function highlightActiveMapButton(mapId) {
    const buttons = elements.mapsList.querySelectorAll(".map-button");

    buttons.forEach((button) => {
        const isActive = Number(button.dataset.mapId) === Number(mapId);
        button.classList.toggle("active", isActive);
    });
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

function getLandmarkColor(type) {
    return LANDMARK_TYPE_COLORS[type] || "#334155";
}
async function fetchJson(url) {
    console.log("Fetching URL:", url);

    const response = await fetch(url, {
        method: "GET",
        headers: {
            "Accept": "application/json"
        }
    });

    console.log("Response status:", response.status, "for", url);

    const text = await response.text();
    console.log("Raw response text:", text);

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