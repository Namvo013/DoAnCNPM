(() => {
  "use strict";

  const apiOrigin = new URL(window.location.origin);
  if (apiOrigin.port === "5500") apiOrigin.port = "8000";
  const API_BASE = apiOrigin.origin;
  const OVERPASS_API = "https://overpass-api.de/api/interpreter";
  const SUPPORTED_LANGUAGES = ["vi", "en", "ja", "ko", "zh"];
  const LANGUAGE_NAMES = { vi: "Tiếng Việt", en: "English", ja: "日本語", ko: "한국어", zh: "中文" };
  const params = new URLSearchParams(location.search);
  const initialLanguage = SUPPORTED_LANGUAGES.includes(params.get("lang")) ? params.get("lang") : "vi";
  let selectedLanguage = initialLanguage;
  let sessionId = createSessionId();
  let serverVisitorId = null;
  let socket = null;
  let reconnectTimer = null;
  let reconnectDelay = 1000;
  let heartbeatTimer = null;
  let watchId = null;
  let pageLeaving = false;
  let map = null;
  let userMarker = null;
  let accuracyCircle = null;
  let selectedPoiId = null;
  let currentPoiId = null;
  let currentPosition = null;
  let locationSamples = [];
  let pois = [];
  let markers = new Map();
  let poiGeofences = new Map();
  let enteredPois = new Set();
  let playedPois = new Set();
  let activeAuxView = "map";
  let amenitiesRequested = false;
  let amenitiesRequestId = 0;

  const $ = (id) => document.getElementById(id);
  const elements = {
    welcome: $("welcome-screen"),
    main: $("main-screen"),
    languageOptions: $("language-options"),
    enterMap: $("enter-map"),
    currentLanguage: $("current-language"),
    error: $("app-error"),
    locationPrompt: $("location-prompt"),
    locationTitle: $("location-title"),
    locationDescription: $("location-description"),
    enableLocation: $("enable-location"),
    poiTotal: $("poi-total"),
    listTotal: $("list-total"),
    map: $("map"),
    mapFallback: $("map-fallback"),
    detail: $("poi-detail-content"),
    poiList: $("poi-list"),
    auxPanel: $("aux-panel"),
    player: $("audio-player"),
    audio: $("audio-element"),
    playerName: $("player-poi-name"),
    playerToggle: $("player-toggle"),
    progress: $("audio-progress"),
    audioTime: $("audio-time"),
    seekBack: $("seek-back"),
    seekForward: $("seek-forward"),
    bottomNav: $("bottom-nav"),
    networkBanner: $("network-banner")
  };

  function createSessionId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return `tour-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  function apiUrl(path) {
    return `${API_BASE}${path}`;
  }

  function translateApiDetail(detail) {
    const known = {
      "POI not found": "Không tìm thấy điểm tham quan.",
      "POI has no published content": "Điểm tham quan chưa có nội dung được xuất bản.",
      "Expected a heartbeat message": "Dữ liệu kết nối không hợp lệ. Đang thử kết nối lại.",
      "Latitude and longitude must be provided together": "Tọa độ vị trí không đầy đủ.",
      "Not Found": "Không tìm thấy nội dung được yêu cầu.",
      "Internal Server Error": "Máy chủ gặp sự cố. Vui lòng thử lại sau."
    };
    if (typeof detail === "string") return known[detail] || `Máy chủ phản hồi: ${detail}`;
    if (Array.isArray(detail)) {
      const messages = detail.map((item) => {
        const field = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "";
        if (item.type === "missing") return `Thiếu thông tin${field ? `: ${field}` : ""}.`;
        if (item.type === "greater_than_equal") return `${field || "Giá trị"} nhỏ hơn mức cho phép.`;
        if (item.type === "less_than_equal") return `${field || "Giá trị"} vượt quá mức cho phép.`;
        return field ? `Thông tin ${field} chưa hợp lệ.` : "Thông tin gửi lên chưa hợp lệ.";
      });
      return messages.join(" ");
    }
    return "Không thể hoàn tất yêu cầu. Vui lòng thử lại.";
  }

  async function requestJson(path) {
    let response;
    try {
      response = await fetch(apiUrl(path), { headers: { Accept: "application/json" } });
    } catch (error) {
      throw new Error(navigator.onLine ? "Không thể kết nối máy chủ. Vui lòng thử lại." : "Không có kết nối mạng.");
    }
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      if (response.ok) throw new Error("Máy chủ trả về dữ liệu không đọc được.");
    }
    if (!response.ok) throw new Error(translateApiDetail(payload.detail));
    return payload;
  }

  function showError(message) {
    elements.error.textContent = message;
    elements.error.hidden = false;
  }

  function clearError() {
    elements.error.textContent = "";
    elements.error.hidden = true;
  }

  function setNetworkState() {
    elements.networkBanner.hidden = navigator.onLine;
    if (navigator.onLine) connectSocket();
  }

  function connectSocket() {
    if (!navigator.onLine || (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING))) return;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    const protocol = apiOrigin.protocol === "https:" ? "wss:" : "ws:";
    const query = new URLSearchParams({ language: selectedLanguage, session_id: sessionId });
    try {
      socket = new WebSocket(`${protocol}//${apiOrigin.host}/ws/tourist?${query}`);
    } catch (error) {
      scheduleReconnect();
      return;
    }
    socket.addEventListener("open", () => {
      reconnectDelay = 1000;
      startHeartbeat();
    });
    socket.addEventListener("message", (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch (error) {
        showError("Máy chủ gửi thông báo không hợp lệ.");
        return;
      }
      handleSocketMessage(message);
    });
    socket.addEventListener("error", () => {
      if (navigator.onLine) showError("Kết nối thời gian thực bị gián đoạn. Đang thử kết nối lại.");
    });
    socket.addEventListener("close", () => {
      stopHeartbeat();
      serverVisitorId = null;
      scheduleReconnect();
    });
  }

  function scheduleReconnect() {
    if (!navigator.onLine || pageLeaving || reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectSocket();
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
  }

  function startHeartbeat() {
    stopHeartbeat();
    sendHeartbeat();
    heartbeatTimer = setInterval(sendHeartbeat, 15000);
  }

  function stopHeartbeat() {
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }

  function sendHeartbeat() {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    const heartbeat = {
      type: "heartbeat",
      language: selectedLanguage,
      poi_id: currentPoiId
    };
    if (currentPosition) {
      heartbeat.latitude = currentPosition.latitude;
      heartbeat.longitude = currentPosition.longitude;
    }
    socket.send(JSON.stringify(heartbeat));
  }

  function handleSocketMessage(message) {
    if (message.type === "connected") {
      serverVisitorId = message.visitor_id || null;
      sendHeartbeat();
    } else if (message.type === "error" && message.detail) {
      showError(translateApiDetail(message.detail));
    }
  }

  function selectLanguage(language) {
    if (!SUPPORTED_LANGUAGES.includes(language)) return;
    selectedLanguage = language;
    elements.enterMap.disabled = false;
    document.querySelectorAll(".language-choice").forEach((button) => {
      const active = button.dataset.language === language;
      button.classList.toggle("is-selected", active);
      button.setAttribute("aria-pressed", String(active));
    });
    const option = elements.currentLanguage.querySelector(`option[value="${language}"]`);
    if (option) option.selected = true;
  }

  function enterMap() {
    elements.welcome.hidden = true;
    elements.main.hidden = false;
    elements.bottomNav.hidden = false;
    initializeMap();
    loadPois();
    connectSocket();
  }

  function initializeMap() {
    if (map) return map;
    if (!window.L) {
      elements.mapFallback.textContent = "Không tải được thư viện bản đồ. Kiểm tra kết nối Internet.";
      elements.mapFallback.hidden = false;
      showError(elements.mapFallback.textContent);
      return null;
    }
    map = L.map(elements.map).setView([16.0471, 108.2068], 5);
    const streets = L.tileLayer("https://tile.openstreetmap.de/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    const satellite = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        maxZoom: 19,
        attribution: "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community"
      }
    );
    L.control.layers({ "Đường phố": streets, "Vệ tinh": satellite }).addTo(map);
    elements.mapFallback.hidden = true;
    renderPois();
    window.setTimeout(() => map?.invalidateSize(), 100);
    return map;
  }

  function mediaUrl(value) {
    if (!value) return "";
    try {
      return new URL(value, `${API_BASE}/`).href;
    } catch (error) {
      return "";
    }
  }

  async function loadPois() {
    elements.poiTotal.textContent = "Đang tải…";
    try {
      const payload = await requestJson(`/api/pois?language=${encodeURIComponent(selectedLanguage)}&limit=100`);
      pois = Array.isArray(payload.items) ? payload.items : [];
      renderPois();
      clearError();
    } catch (error) {
      elements.poiTotal.textContent = "Chưa tải được";
      elements.poiList.replaceChildren(makeText("p", error.message, "empty-state"));
      showError(error.message);
    }
  }

  function makeText(tag, text, className) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    return node;
  }

  function renderPois() {
    elements.poiTotal.textContent = `${pois.length} điểm`;
    elements.listTotal.textContent = `${pois.length} điểm`;
    elements.poiList.replaceChildren();
    markers.forEach((marker) => marker.remove());
    poiGeofences.forEach((circle) => circle.remove());
    markers.clear();
    poiGeofences.clear();
    if (pois.length === 0) {
      elements.poiList.append(makeText("p", "Chưa có điểm tham quan khả dụng.", "empty-state"));
      if (map) elements.mapFallback.textContent = "Bản đồ đã sẵn sàng. Chưa có POI hoạt động để hiển thị.";
      if (map) elements.mapFallback.hidden = false;
      if (currentPosition) updateUserMarker();
      return;
    }
    const bounds = map ? L.latLngBounds([]) : null;
    let count = 0;
    pois.forEach((poi) => {
      const lat = poi.coordinates && Number(poi.coordinates.latitude);
      const lng = poi.coordinates && Number(poi.coordinates.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
      const position = [lat, lng];
      bounds?.extend(position);
      count += 1;
      if (map) {
        const marker = L.circleMarker(position, {
          radius: 9,
          color: "#0B0B0B",
          weight: 3,
          fillColor: "#FFC107",
          fillOpacity: 1
        }).addTo(map);
        const imageUrl = mediaUrl(poi.image_url);
        marker.bindPopup(
          `<div class="poi-map-popup"><strong>${escapeHtml(poi.name || "Điểm tham quan")}</strong>`
          + (imageUrl ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(`Ảnh ${poi.name || "điểm tham quan"}`)}">` : "")
          + `<small>${escapeHtml(poi.category || "Điểm tham quan")}</small></div>`
        );
        marker.on("click", () => {
          selectPoi(poi.id, false);
        });
        markers.set(poi.id, marker);
        poiGeofences.set(poi.id, L.circle(position, {
          radius: Number(poi.geofence_radius_m) || 30,
          color: "#FFC107",
          weight: 1,
          opacity: .6,
          fillColor: "#FFC107",
          fillOpacity: .08,
          interactive: false
        }).addTo(map));
      }
      elements.poiList.append(createPoiCard(poi));
    });
    if (map && count === 1) {
      map.setView(bounds.getCenter(), 15);
      elements.mapFallback.hidden = true;
    } else if (map && count > 1) {
      map.fitBounds(bounds, { padding: [30, 30] });
      elements.mapFallback.hidden = true;
    } else if (map && count === 0) {
      elements.mapFallback.textContent = "Bản đồ đã sẵn sàng. Chưa có POI với tọa độ hợp lệ để hiển thị.";
      elements.mapFallback.hidden = false;
    }
    if (!elements.poiList.childElementCount) {
      elements.poiList.append(makeText("p", "Chưa có tọa độ điểm tham quan hợp lệ.", "empty-state"));
    }
    if (selectedPoiId && pois.some((poi) => poi.id === selectedPoiId)) selectPoi(selectedPoiId, false);
    if (currentPosition) detectGeofence();
    if (currentPosition) updateUserMarker();
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
    })[character]);
  }

  function createPoiCard(poi) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "poi-card";
    button.dataset.poiId = poi.id;
    button.setAttribute("aria-label", `Xem ${poi.name || "điểm tham quan"}`);
    if (poi.image_url) {
      const image = document.createElement("img");
      image.src = mediaUrl(poi.image_url);
      image.alt = "";
      image.loading = "lazy";
      image.addEventListener("error", () => image.remove(), { once: true });
      button.append(image);
    }
    const copy = document.createElement("span");
    copy.className = "poi-card-copy";
    copy.append(makeText("strong", poi.name || "Điểm tham quan"));
    copy.append(makeText("small", `${poi.category || "Điểm tham quan"} · Bán kính ${poi.geofence_radius_m || 0} m`));
    button.append(copy, makeText("span", "›", "poi-card-arrow"));
    button.addEventListener("click", () => selectPoi(poi.id, true));
    return button;
  }

  function selectPoi(poiId, panTo) {
    const poi = pois.find((item) => item.id === poiId);
    if (!poi) return;
    selectedPoiId = poi.id;
    document.querySelectorAll(".poi-card").forEach((card) => {
      const selected = card.dataset.poiId === poi.id;
      card.classList.toggle("is-selected", selected);
      if (selected) card.setAttribute("aria-current", "true");
      else card.removeAttribute("aria-current");
    });
    renderPoiDetail(poi);
    const marker = markers.get(poi.id);
    if (panTo && map && marker) {
      map.setView(marker.getLatLng(), Math.max(map.getZoom(), 16));
    }
    if (marker && panTo) marker.openPopup();
  }

  function renderPoiDetail(poi) {
    elements.detail.replaceChildren();
    elements.detail.append(makeText("h2", poi.name || "Điểm tham quan", "poi-detail-title"));
    if (poi.image_url) {
      const image = document.createElement("img");
      image.src = mediaUrl(poi.image_url);
      image.alt = `Ảnh ${poi.name || "điểm tham quan"}`;
      image.loading = "lazy";
      image.addEventListener("error", () => image.remove(), { once: true });
      elements.detail.append(image);
    }
    const contentLanguage = poi.content_language || Object.keys(poi.content || {})[0] || selectedLanguage;
    const description = poi.content && (poi.content[contentLanguage] || Object.values(poi.content)[0]);
    if (description) elements.detail.append(makeText("p", description));
    elements.detail.append(makeText("p", `${poi.category || "Điểm tham quan"} · Bán kính ${poi.geofence_radius_m || 0} m · ${LANGUAGE_NAMES[contentLanguage] || contentLanguage}`, "poi-meta"));
    const audioUrl = getAudioUrl(poi);
    const play = makeText("button", audioUrl ? "▶  Nghe thuyết minh" : "Chưa có audio thuyết minh");
    play.type = "button";
    play.className = "button button-primary poi-audio-button";
    play.disabled = !audioUrl;
    play.addEventListener("click", () => playPoiAudio(poi, false));
    elements.detail.append(play);
  }

  function getAudioUrl(poi) {
    const audio = poi.audio || {};
    const actualLanguage = poi.content_language;
    const url = audio[selectedLanguage] || (actualLanguage && audio[actualLanguage]) || audio.en || audio.vi;
    return mediaUrl(url);
  }

  function handleLocation(position) {
    const { latitude, longitude, accuracy } = position.coords;
    if (accuracy > 50) {
      elements.locationTitle.textContent = "Tín hiệu GPS chưa chính xác";
      elements.locationDescription.textContent = `Độ chính xác hiện tại khoảng ${Math.round(accuracy)} m. Hãy di chuyển ra nơi thoáng hơn để nhận diện điểm.`;
      return;
    }
    locationSamples.push({ latitude, longitude });
    if (locationSamples.length > 3) locationSamples.shift();
    currentPosition = {
      latitude: locationSamples.reduce((sum, item) => sum + item.latitude, 0) / locationSamples.length,
      longitude: locationSamples.reduce((sum, item) => sum + item.longitude, 0) / locationSamples.length
    };
    elements.locationTitle.textContent = "Định vị đang hoạt động";
    elements.locationDescription.textContent = "Khi đến gần điểm tham quan, ứng dụng sẽ tự nhận biết và phát thuyết minh.";
    updateUserMarker(accuracy);
    detectGeofence();
    sendHeartbeat();
    if (activeAuxView === "amenities" && amenitiesRequested) {
      amenitiesRequested = false;
      loadNearbyAmenities();
    }
  }

  function updateUserMarker(accuracy) {
    if (!map || !currentPosition) return;
    const position = { lat: currentPosition.latitude, lng: currentPosition.longitude };
    if (!userMarker) {
      userMarker = L.circleMarker([currentPosition.latitude, currentPosition.longitude], {
        radius: 8,
        color: "#FFFFFF",
        weight: 3,
        fillColor: "#348CFF",
        fillOpacity: 1
      }).addTo(map).bindPopup("Vị trí của bạn");
      map.setView([currentPosition.latitude, currentPosition.longitude], 16);
    } else userMarker.setLatLng([currentPosition.latitude, currentPosition.longitude]);
    if (!accuracyCircle) {
      accuracyCircle = L.circle([currentPosition.latitude, currentPosition.longitude], {
        radius: accuracy,
        color: "#FFC107",
        weight: 1,
        opacity: .35,
        fillColor: "#FFC107",
        fillOpacity: .06,
        interactive: false
      }).addTo(map);
    } else {
      accuracyCircle.setLatLng([currentPosition.latitude, currentPosition.longitude]);
      accuracyCircle.setRadius(accuracy);
    }
  }

  function requestLocation() {
    clearError();
    if (!navigator.geolocation) {
      elements.locationTitle.textContent = "Thiết bị chưa hỗ trợ định vị";
      elements.locationDescription.textContent = "Hãy mở trang này bằng trình duyệt hiện đại trên điện thoại để sử dụng GPS.";
      if (activeAuxView === "amenities" && amenitiesRequested) {
        amenitiesRequested = false;
        const status = $("amenities-status");
        if (status) status.textContent = "Trình duyệt này không hỗ trợ định vị GPS.";
      }
      return;
    }
    elements.locationTitle.textContent = "Đang chờ quyền vị trí";
    elements.locationDescription.textContent = "Chọn Cho phép khi trình duyệt hỏi quyền truy cập vị trí.";
    elements.enableLocation.disabled = true;
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    watchId = navigator.geolocation.watchPosition(handleLocation, handleLocationError, {
      enableHighAccuracy: true,
      maximumAge: 5000,
      timeout: 20000
    });
  }

  function handleLocationError(error) {
    elements.enableLocation.disabled = false;
    if (activeAuxView === "amenities" && amenitiesRequested) {
      amenitiesRequested = false;
      const status = $("amenities-status");
      if (status) status.textContent = "Không lấy được vị trí. Hãy kiểm tra quyền GPS rồi thử lại.";
    }
    if (error.code === error.PERMISSION_DENIED) {
      elements.locationTitle.textContent = "Quyền vị trí đang bị tắt";
      elements.locationDescription.textContent = "Hãy mở Cài đặt trang web trong trình duyệt, bật Vị trí, rồi tải lại trang và nhấn “Bật định vị”.";
    } else if (error.code === error.POSITION_UNAVAILABLE) {
      elements.locationTitle.textContent = "Chưa xác định được vị trí";
      elements.locationDescription.textContent = "Kiểm tra GPS của thiết bị và thử lại ở nơi có tín hiệu tốt hơn.";
    } else {
      elements.locationTitle.textContent = "Định vị mất quá nhiều thời gian";
      elements.locationDescription.textContent = "Kiểm tra GPS và nhấn “Bật định vị” để thử lại.";
    }
  }

  function detectGeofence() {
    if (!currentPosition || !window.turf) return;
    const userPoint = turf.point([currentPosition.longitude, currentPosition.latitude]);
    let nearestInside = null;
    let nearestDistance = Infinity;
    const insideNow = new Set();
    for (const poi of pois) {
      const latitude = Number(poi.coordinates && poi.coordinates.latitude);
      const longitude = Number(poi.coordinates && poi.coordinates.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) continue;
      const poiPoint = turf.point([longitude, latitude]);
      const distance = turf.distance(userPoint, poiPoint, { units: "kilometers" }) * 1000;
      const radius = Number(poi.geofence_radius_m);
      if (Number.isFinite(radius) && distance <= radius) {
        insideNow.add(poi.id);
        if (distance < nearestDistance) {
          nearestDistance = distance;
          nearestInside = poi;
        }
      }
    }
    for (const id of enteredPois) {
      if (!insideNow.has(id)) playedPois.delete(id);
    }
    enteredPois = insideNow;
    if (!nearestInside) {
      if (currentPoiId !== null) {
        currentPoiId = null;
        sendHeartbeat();
      }
      return;
    }
    if (currentPoiId !== nearestInside.id) {
      currentPoiId = nearestInside.id;
      selectPoi(nearestInside.id, false);
      sendHeartbeat();
    }
    if (!playedPois.has(nearestInside.id)) {
      playedPois.add(nearestInside.id);
      playPoiAudio(nearestInside, true);
    }
  }

  function playPoiAudio(poi, automatic) {
    const src = getAudioUrl(poi);
    if (!src) {
      if (automatic) {
        elements.locationTitle.textContent = "Bạn đã đến điểm tham quan";
        elements.locationDescription.textContent = `${poi.name}: hiện chưa có audio thuyết minh được xuất bản.`;
      }
      return;
    }
    elements.player.hidden = false;
    elements.playerName.textContent = poi.name || "Điểm tham quan";
    elements.audio.src = src;
    elements.playerToggle.disabled = false;
    elements.seekBack.disabled = false;
    elements.seekForward.disabled = false;
    elements.progress.disabled = false;
    updateMediaSession(poi);
    const playPromise = elements.audio.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise.catch(() => {
        elements.playerToggle.textContent = "▶";
        elements.playerToggle.setAttribute("aria-label", "Phát");
        if (automatic) {
          elements.locationTitle.textContent = "Chạm để phát thuyết minh";
          elements.locationDescription.textContent = `Đã nhận diện ${poi.name}. Trình duyệt yêu cầu bạn chạm nút phát.`;
        } else {
          showError("Trình duyệt chưa thể phát audio. Hãy nhấn nút phát và kiểm tra kết nối mạng.");
        }
      });
    }
  }

  function togglePlayback() {
    if (!elements.audio.src) return;
    if (elements.audio.paused) elements.audio.play().catch(() => showError("Không thể phát audio. Vui lòng thử lại."));
    else elements.audio.pause();
  }

  function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.floor(seconds % 60).toString().padStart(2, "0");
    return `${minutes}:${remainder}`;
  }

  function updateProgress() {
    const duration = elements.audio.duration;
    const current = elements.audio.currentTime || 0;
    elements.progress.value = duration ? String((current / duration) * 100) : "0";
    elements.audioTime.textContent = `${formatTime(current)} / ${formatTime(duration)}`;
    if (duration && navigator.mediaSession && navigator.mediaSession.setPositionState) {
      try {
        navigator.mediaSession.setPositionState({ duration, playbackRate: elements.audio.playbackRate, position: current });
      } catch (error) {
        // The browser may reject position updates while media metadata is still loading.
      }
    }
  }

  function updateMediaSession(poi) {
    if (!("mediaSession" in navigator) || typeof MediaMetadata === "undefined") return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: poi.name || "Điểm tham quan",
      artist: "Thuyết minh du lịch",
      album: "Hướng dẫn theo vị trí",
      artwork: poi.image_url ? [{ src: mediaUrl(poi.image_url), sizes: "512x512" }] : []
    });
    const actions = {
      play: () => elements.audio.play().catch(() => {}),
      pause: () => elements.audio.pause(),
      seekbackward: (details) => { elements.audio.currentTime = Math.max(0, elements.audio.currentTime - (details.seekOffset || 10)); },
      seekforward: (details) => { elements.audio.currentTime = Math.min(elements.audio.duration || Infinity, elements.audio.currentTime + (details.seekOffset || 10)); },
      seekto: (details) => { if (Number.isFinite(details.seekTime)) elements.audio.currentTime = details.seekTime; }
    };
    for (const [action, handler] of Object.entries(actions)) {
      try {
        navigator.mediaSession.setActionHandler(action, handler);
      } catch (error) {
        // Some browsers expose only a subset of media-session actions.
      }
    }
  }

  function showAuxiliaryView(view) {
    const labels = { amenities: "Ẩm thực", assistant: "Trợ lý AI", groups: "Nhóm" };
    activeAuxView = view;
    if (view !== "amenities") {
      amenitiesRequested = false;
      amenitiesRequestId += 1;
    }
    document.querySelectorAll(".nav-item").forEach((button) => {
      const active = button.dataset.view === view;
      button.classList.toggle("is-active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    if (view === "map") {
      activeAuxView = "map";
      elements.auxPanel.hidden = true;
      $("map-section").hidden = false;
      $("selected-poi").hidden = false;
      $("poi-list-section").hidden = false;
      if (map) setTimeout(() => map.invalidateSize(), 50);
      return;
    }
    $("map-section").hidden = true;
    $("selected-poi").hidden = true;
    $("poi-list-section").hidden = true;
    elements.auxPanel.hidden = false;
    elements.auxPanel.replaceChildren();
    elements.auxPanel.append(makeText("p", labels[view].toUpperCase(), "eyebrow"));
    elements.auxPanel.append(makeText("h1", labels[view]));
    if (view === "amenities") {
      renderAmenitiesPanel();
      if (currentPosition) loadNearbyAmenities();
      return;
    }
    const descriptions = {
      assistant: "Trợ lý AI chưa được tích hợp trong phiên bản này. Nội dung thuyết minh và phát audio theo vị trí vẫn hoạt động bình thường.",
      groups: "Chức năng nhóm chưa được triển khai. Bạn vẫn có thể tự khám phá và nghe thuyết minh tại từng điểm tham quan.",
    };
    elements.auxPanel.append(makeText("span", "ĐANG PHÁT TRIỂN", "feature-status"));
    elements.auxPanel.append(makeText("p", descriptions[view], "feature-description"));
    const returnButton = makeText("button", "Quay lại bản đồ");
    returnButton.type = "button";
    returnButton.className = "button button-secondary";
    returnButton.addEventListener("click", () => showAuxiliaryView("map"));
    elements.auxPanel.append(returnButton);
  }

  function renderAmenitiesPanel() {
    const description = makeText(
      "p",
      "Tìm nhà hàng, quán cà phê và quán ăn gần vị trí của bạn. Dữ liệu do OpenStreetMap cung cấp; khi tìm kiếm, tọa độ hiện tại được gửi tới dịch vụ Overpass API.",
      "feature-description"
    );
    elements.auxPanel.append(description);

    const controls = document.createElement("div");
    controls.className = "amenities-controls";
    const label = document.createElement("label");
    label.className = "amenity-radius-label";
    label.htmlFor = "amenity-radius";
    label.textContent = "Tìm trong bán kính";
    const radius = document.createElement("select");
    radius.id = "amenity-radius";
    radius.setAttribute("aria-label", "Bán kính tìm địa điểm ăn uống");
    [
      ["500", "500 m"],
      ["1000", "1 km"],
      ["1500", "1,5 km"],
      ["3000", "3 km"],
    ].forEach(([value, text]) => {
      const option = makeText("option", text);
      option.value = value;
      option.selected = value === "1500";
      radius.append(option);
    });
    label.append(radius);

    const searchButton = makeText("button", currentPosition ? "Tìm quanh tôi" : "Bật định vị");
    searchButton.type = "button";
    searchButton.className = "button button-primary";
    searchButton.id = "amenities-search";
    searchButton.addEventListener("click", () => {
      if (!currentPosition) {
        amenitiesRequested = true;
        const status = $("amenities-status");
        status.textContent = "Đang chờ vị trí GPS. Hãy cho phép truy cập vị trí khi trình duyệt hỏi.";
        requestLocation();
        return;
      }
      loadNearbyAmenities();
    });
    controls.append(label, searchButton);
    elements.auxPanel.append(controls);
    elements.auxPanel.append(makeText(
      "p",
      currentPosition ? "Kết quả được sắp xếp theo khoảng cách gần nhất." : "Bật định vị để tìm địa điểm quanh bạn.",
      "amenities-hint"
    ));
    const status = makeText("p", "Đang tải địa điểm ăn uống…", "amenities-status");
    status.id = "amenities-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    elements.auxPanel.append(status);
    const list = document.createElement("div");
    list.id = "amenities-list";
    list.className = "amenities-list";
    elements.auxPanel.append(list);
    const attribution = makeText("small", "© OpenStreetMap contributors · Dữ liệu có thể thiếu hoặc chưa cập nhật. ", "amenities-attribution");
    const attributionLink = document.createElement("a");
    attributionLink.href = "https://www.openstreetmap.org/copyright";
    attributionLink.target = "_blank";
    attributionLink.rel = "noopener noreferrer";
    attributionLink.textContent = "Thông tin bản quyền";
    attribution.append(attributionLink);
    elements.auxPanel.append(attribution);
    if (currentPosition) {
      $("amenities-status").textContent = "Sẵn sàng tìm kiếm quanh vị trí hiện tại.";
    } else {
      $("amenities-status").textContent = "Cần bật định vị để tìm địa điểm gần bạn.";
    }
  }

  function distanceInMeters(from, to) {
    const radians = (degrees) => degrees * Math.PI / 180;
    const latitudeDelta = radians(to.latitude - from.latitude);
    const longitudeDelta = radians(to.longitude - from.longitude);
    const a = Math.sin(latitudeDelta / 2) ** 2
      + Math.cos(radians(from.latitude)) * Math.cos(radians(to.latitude))
      * Math.sin(longitudeDelta / 2) ** 2;
    return 6371000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function amenityType(tags) {
    const labels = {
      restaurant: "Nhà hàng",
      cafe: "Quán cà phê",
      fast_food: "Đồ ăn nhanh",
      food_court: "Khu ẩm thực",
      ice_cream: "Kem",
    };
    return labels[tags.amenity] || "Địa điểm ăn uống";
  }

  function formatDistance(meters) {
    return meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`;
  }

  function renderAmenities(items) {
    const list = $("amenities-list");
    list.replaceChildren();
    if (!items.length) {
      list.append(makeText("p", "Không tìm thấy địa điểm ăn uống trong bán kính đã chọn. Thử tăng bán kính hoặc tìm lại sau.", "empty-state"));
      return;
    }

    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "amenity-card";
      const heading = document.createElement("div");
      heading.className = "amenity-card-heading";
      const name = item.tags.name || item.tags["name:vi"] || item.tags.brand || "Địa điểm ăn uống (chưa có tên)";
      heading.append(makeText("h2", name), makeText("span", amenityType(item.tags), "amenity-type"));
      card.append(heading);
      card.append(makeText("p", `Cách bạn ${formatDistance(item.distance)}`, "amenity-distance"));
      const address = [
        item.tags["addr:housenumber"],
        item.tags["addr:street"],
        item.tags["addr:suburb"],
        item.tags["addr:city"],
      ].filter(Boolean).join(", ");
      if (address) card.append(makeText("p", address, "amenity-address"));

      const actions = document.createElement("div");
      actions.className = "amenity-actions";
      const directions = document.createElement("a");
      directions.className = "button button-secondary";
      directions.textContent = "Chỉ đường";
      directions.href = `https://www.google.com/maps/dir/?api=1&destination=${item.latitude},${item.longitude}`;
      directions.target = "_blank";
      directions.rel = "noopener noreferrer";
      actions.append(directions);
      const website = item.tags.website || item.tags["contact:website"];
      if (website) {
        try {
          const websiteUrl = new URL(/^https?:\/\//i.test(website) ? website : `https://${website}`);
          if (websiteUrl.protocol === "http:" || websiteUrl.protocol === "https:") {
            const link = document.createElement("a");
            link.className = "button button-secondary";
            link.textContent = "Trang web";
            link.href = websiteUrl.href;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            actions.append(link);
          }
        } catch (error) {
          // Ignore malformed contact details from the public map data.
        }
      }
      card.append(actions);
      list.append(card);
    });
  }

  async function loadNearbyAmenities() {
    if (!currentPosition || !$("amenities-status") || !$("amenities-list")) return;
    const requestId = ++amenitiesRequestId;
    const searchPosition = { ...currentPosition };
    const radius = Number($("amenity-radius").value) || 1500;
    const status = $("amenities-status");
    const searchButton = $("amenities-search");
    status.textContent = "Đang tìm địa điểm ăn uống gần bạn…";
    searchButton.disabled = true;
    searchButton.textContent = "Đang tìm…";
    $("amenities-list").replaceChildren();

    const query = `[out:json][timeout:20];(node["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream)$"](around:${radius},${searchPosition.latitude},${searchPosition.longitude});way["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream)$"](around:${radius},${searchPosition.latitude},${searchPosition.longitude});relation["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream)$"](around:${radius},${searchPosition.latitude},${searchPosition.longitude}););out center tags;`;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 25000);
    try {
      const response = await fetch(OVERPASS_API, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        body: new URLSearchParams({ data: query }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Dịch vụ bản đồ phản hồi lỗi (${response.status}).`);
      const payload = await response.json();
      const seen = new Set();
      const results = (Array.isArray(payload.elements) ? payload.elements : [])
        .map((element) => {
          const latitude = Number(element.lat ?? element.center?.lat);
          const longitude = Number(element.lon ?? element.center?.lon);
          const tags = element.tags || {};
          if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || seen.has(`${element.type}/${element.id}`)) return null;
          seen.add(`${element.type}/${element.id}`);
          return {
            latitude,
            longitude,
            tags,
            distance: distanceInMeters(searchPosition, { latitude, longitude }),
          };
        })
        .filter((item) => item && item.distance <= radius)
        .sort((left, right) => left.distance - right.distance);
      if (requestId !== amenitiesRequestId) return;
      renderAmenities(results);
      status.textContent = `${results.length} địa điểm trong bán kính ${radius < 1000 ? `${radius} m` : `${radius / 1000} km`}.`;
    } catch (error) {
      if (requestId !== amenitiesRequestId) return;
      status.textContent = error.name === "AbortError"
        ? "Tìm kiếm quá thời gian chờ. Hãy thử lại."
        : `Không tải được dữ liệu ẩm thực: ${error.message}`;
      const retryButton = makeText("button", "Thử lại", "amenities-retry");
      retryButton.type = "button";
      retryButton.addEventListener("click", loadNearbyAmenities);
      $("amenities-list").append(retryButton);
    } finally {
      window.clearTimeout(timeout);
      if (requestId === amenitiesRequestId && $("amenities-search")) {
        searchButton.disabled = false;
        searchButton.textContent = "Tìm quanh tôi";
      }
    }
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("./service-worker.js").catch(() => {
      showError("Không thể bật chế độ PWA ngoại tuyến. Trang vẫn có thể sử dụng khi có mạng.");
    });
  }

  document.querySelectorAll(".language-choice").forEach((button) => {
    button.addEventListener("click", () => selectLanguage(button.dataset.language));
  });
  elements.enterMap.addEventListener("click", enterMap);
  elements.enableLocation.addEventListener("click", requestLocation);
  elements.currentLanguage.addEventListener("change", (event) => {
    const language = event.target.value;
    if (!SUPPORTED_LANGUAGES.includes(language)) return;
    selectedLanguage = language;
    sessionId = createSessionId();
    enteredPois = new Set();
    playedPois = new Set();
    pois = [];
    selectedPoiId = null;
    currentPoiId = null;
    if (socket) socket.close();
    loadPois();
    connectSocket();
  });
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => showAuxiliaryView(button.dataset.view));
  });
  elements.playerToggle.addEventListener("click", togglePlayback);
  elements.seekBack.addEventListener("click", () => { elements.audio.currentTime = Math.max(0, elements.audio.currentTime - 10); });
  elements.seekForward.addEventListener("click", () => { elements.audio.currentTime = Math.min(elements.audio.duration || Infinity, elements.audio.currentTime + 10); });
  elements.progress.addEventListener("input", () => {
    if (elements.audio.duration) elements.audio.currentTime = (Number(elements.progress.value) / 100) * elements.audio.duration;
  });
  elements.audio.addEventListener("timeupdate", updateProgress);
  elements.audio.addEventListener("loadedmetadata", updateProgress);
  elements.audio.addEventListener("play", () => {
    elements.playerToggle.textContent = "Ⅱ";
    elements.playerToggle.setAttribute("aria-label", "Tạm dừng");
    if (navigator.mediaSession) navigator.mediaSession.playbackState = "playing";
  });
  elements.audio.addEventListener("pause", () => {
    elements.playerToggle.textContent = "▶";
    elements.playerToggle.setAttribute("aria-label", "Phát");
    if (navigator.mediaSession) navigator.mediaSession.playbackState = "paused";
  });
  elements.audio.addEventListener("ended", () => {
    elements.playerToggle.textContent = "▶";
    elements.playerToggle.setAttribute("aria-label", "Phát");
  });
  elements.audio.addEventListener("error", () => {
    if (elements.audio.src) showError("Không tải được audio thuyết minh. Hãy kiểm tra kết nối mạng.");
  });
  window.addEventListener("online", setNetworkState);
  window.addEventListener("offline", setNetworkState);
  window.addEventListener("pagehide", () => {
    pageLeaving = true;
    if (watchId !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId);
    stopHeartbeat();
    if (socket) socket.close();
  });
  window.addEventListener("pageshow", () => {
    pageLeaving = false;
    if (!socket || socket.readyState === WebSocket.CLOSED) connectSocket();
  });

  selectLanguage(initialLanguage);
  connectSocket();
  setNetworkState();
  registerServiceWorker();
})();
