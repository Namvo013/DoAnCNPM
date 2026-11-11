const API_ORIGIN_URL = new URL(window.location.origin);
if (API_ORIGIN_URL.port === "5500") API_ORIGIN_URL.port = "8000";
const API_ORIGIN = API_ORIGIN_URL.origin;
const API_ROOT = `${API_ORIGIN}/api`;
const LANGUAGES = [
  ["vi", "Tiếng Việt"],
  ["en", "English"],
  ["ja", "日本語"],
  ["ko", "한국어"],
  ["zh", "中文"],
];
const ROLE_LABELS = {
  super_admin: "Quản trị cao nhất",
  area_operator: "Vận hành khu vực",
  content_editor: "Biên tập nội dung",
  analytics_viewer: "Xem báo cáo",
};
const NAV_ITEMS = [
  ["overview", "Tổng quan", "◫", null],
  ["pois", "Điểm tham quan", "⌖", "poi:read"],
  ["monitor", "Giám sát", "◉", "visitor:read"],
  ["reports", "Báo cáo", "▤", "analytics:read"],
  ["admins", "Tài khoản", "♙", "super_admin"],
];

let currentAdmin;
let poiItems = [];
let poiTotal = 0;
let poiPage = 1;
const poiPageSize = 10;
let selectedTranslationLanguage = "en";
let pickerMap;
let pickerMarker;
let lastMapSearchAt = 0;
let translationPreviewTimer;
let translationPreviewRequest = 0;
let lastPreviewedSource = "";
let fieldTranslationTimer;
let fieldTranslationRequest = 0;
let lastFieldTranslationSource = "";
let poiNameTranslations = {};
let poiCategoryTranslations = {};
let poiImagePreviewObjectUrl;
let heatMap;
let heatMapCircles = [];
let heatMapHasAutoFitted = false;
let poiChart;
let dayChart;
let websocket;
let reconnectTimer;
let visitorCountRefreshTimer;
let visitorCountErrorShown = false;
let lastOnlineCount = null;

const byId = (id) => document.getElementById(id);
const hasPermission = (permission) =>
  currentAdmin?.role === "super_admin" ||
  (permission === "super_admin" && currentAdmin?.role === "super_admin") ||
  ({
    area_operator: ["poi:read", "poi:write", "visitor:read", "heatmap:read"],
    content_editor: ["poi:read", "content:write"],
    analytics_viewer: ["analytics:read", "visitor:read", "heatmap:read"],
  }[currentAdmin?.role] || []).includes(permission);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function addBaseMapLayers(targetMap) {
  const streets = L.tileLayer("https://tile.openstreetmap.de/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  });
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    },
  );
  streets.addTo(targetMap);
  L.control.layers({ "Đường phố": streets, "Vệ tinh": satellite }).addTo(targetMap);
}

function localizeDetail(detail, status) {
  if (typeof detail === "string" && /[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i.test(detail)) {
    return detail;
  }
  if (Array.isArray(detail)) {
    return `Dữ liệu chưa hợp lệ: ${detail.map((item) => item.loc?.at(-1) || "trường dữ liệu").join(", ")}.`;
  }
  const known = {
    "Incorrect email or password": "Email hoặc mật khẩu không chính xác.",
    "Invalid credentials": "Email hoặc mật khẩu không chính xác.",
    "Password confirmation failed": "Mật khẩu xác nhận không chính xác.",
    "Insufficient role": "Tài khoản không có quyền thực hiện thao tác này.",
    "Insufficient permission": "Tài khoản không có quyền thực hiện thao tác này.",
    "POI not found": "Không tìm thấy điểm tham quan.",
    "Active POI not found": "Không tìm thấy điểm tham quan đang hoạt động.",
    "A POI cannot be its own parent": "Một điểm tham quan không thể là khu cha của chính nó.",
    "No fields to update": "Bạn chưa nhập thông tin cần cập nhật.",
    "Fields cannot be null": "Một số trường bắt buộc không được để trống.",
    "Vietnamese content is required": "Nội dung tiếng Việt là bắt buộc.",
    "Translation not found": "Chưa có bản dịch cho ngôn ngữ này.",
    "Translation already published": "Bản dịch đã được xuất bản.",
    "Gemini translation is not configured": "Chưa cấu hình GEMINI_API_KEY. Hãy thêm khóa vào backend-api\\.env rồi khởi động lại backend.",
    "One or more active POIs were not found": "Một hoặc nhiều điểm tham quan không tồn tại hoặc đã ngừng hoạt động.",
    "Admin not found": "Không tìm thấy tài khoản quản trị.",
    "Cannot delete your own account": "Bạn không thể tự xóa tài khoản của mình.",
    "Cannot change your own role": "Bạn không thể tự hạ quyền tài khoản của mình.",
    "No report data found for the selected period": "Không có dữ liệu trong khoảng thời gian đã chọn.",
    "Uploaded file is not a supported image": "Ảnh không đúng định dạng. Hãy chọn JPG, PNG, WebP hoặc GIF.",
    "Image file exceeds 10 MB": "Ảnh vượt quá giới hạn 10 MB.",
  };
  if (typeof detail === "string" && known[detail]) return known[detail];
  if (status === 401) return "Phiên đăng nhập không hợp lệ hoặc mật khẩu xác nhận chưa đúng.";
  if (status === 403) return "Tài khoản không có quyền thực hiện thao tác này.";
  if (status === 404) return "Không tìm thấy dữ liệu phù hợp.";
  if (status === 409) return "Dữ liệu bị trùng hoặc xung đột với thông tin hiện có.";
  if (status === 422) return "Dữ liệu chưa hợp lệ. Vui lòng kiểm tra lại các trường đã nhập.";
  if (status === 503) return "Dịch vụ bên ngoài hiện chưa sẵn sàng.";
  if (status >= 500) return "Máy chủ đang gặp sự cố. Vui lòng thử lại sau.";
  return "Không thể hoàn thành yêu cầu. Vui lòng kiểm tra thông tin và thử lại.";
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_ROOT}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error("Không thể kết nối backend. Hãy kiểm tra máy chủ tại http://localhost:8000.");
  }
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) throw new Error(localizeDetail(payload?.detail, response.status));
  return payload;
}

function showToast(message, isError = false) {
  const toast = document.createElement("div");
  toast.className = `toast${isError ? " error" : ""}`;
  toast.textContent = message;
  byId("toast-region").append(toast);
  window.setTimeout(() => toast.remove(), 5000);
}

function setConnection(connected, label) {
  const dot = byId("connection-dot");
  const status = dot?.parentElement;
  if (!status) return;
  status.classList.toggle("connected", connected);
  byId("connection-label").textContent = label;
  byId("overview-connection").textContent = label;
  byId("overview-updated").textContent = connected ? `Cập nhật ${new Date().toLocaleTimeString("vi-VN")}` : "";
}

function renderNavigation() {
  const available = NAV_ITEMS.filter(([, , , permission]) => !permission || hasPermission(permission));
  byId("main-nav").innerHTML = available.map(([id, label, icon]) =>
    `<button type="button" class="nav-link${id === "overview" ? " active" : ""}" data-section="${id}"><span class="nav-icon">${icon}</span><span>${label}</span></button>`
  ).join("");
  byId("main-nav").addEventListener("click", (event) => {
    const button = event.target.closest("[data-section]");
    if (button) showSection(button.dataset.section);
  });
}

function showSection(section) {
  document.querySelectorAll(".page-section").forEach((item) => item.classList.toggle("active", item.id === `section-${section}`));
  document.querySelectorAll(".nav-link").forEach((item) => item.classList.toggle("active", item.dataset.section === section));
  const selected = NAV_ITEMS.find(([id]) => id === section);
  byId("page-title").textContent = selected?.[1] || "Tổng quan";
  byId("page-eyebrow").textContent = (selected?.[1] || "TỔNG QUAN").toLocaleUpperCase("vi-VN");
  if (section === "pois") loadPoiPage();
  if (section === "monitor") {
    loadHeatmap();
    loadPublicPois();
  }
  if (section === "reports") {
    if (!byId("report-start").value) setReportDates();
  }
  if (section === "admins") loadAdmins();
}

async function initialize() {
  try {
    currentAdmin = await request("/auth/me");
  } catch {
    window.location.replace("login.html");
    return;
  }
  if (currentAdmin.display_name === "Super administrator (demo)") {
    currentAdmin.display_name = "Admin nhóm 2";
  }
  const displayName = currentAdmin.display_name || currentAdmin.email;
  byId("user-name").textContent = displayName;
  byId("user-role").textContent = ROLE_LABELS[currentAdmin.role] || currentAdmin.role;
  byId("user-avatar").textContent = displayName.slice(0, 1).toLocaleUpperCase("vi-VN");
  byId("welcome-name").textContent = displayName;
  byId("add-poi-button").hidden = !hasPermission("poi:write");
  byId("stat-visits-card").hidden = !hasPermission("visitor:read");
  renderNavigation();
  bindControls();
  await Promise.allSettled([loadOverview()]);
  connectAdminSocket();
  if (hasPermission("visitor:read")) {
    visitorCountRefreshTimer = window.setInterval(refreshVisitorCount, 1_000);
  }
}

async function loadOverview() {
  const [poiResult, visitsResult] = await Promise.allSettled([
    request("/pois?limit=100&language=vi"),
    hasPermission("visitor:read") ? request(getTodayVisitorCountPath()) : Promise.resolve(null),
  ]);
  if (poiResult.status === "fulfilled") byId("stat-pois").textContent = poiResult.value.total;
  if (visitsResult.status === "fulfilled" && visitsResult.value) {
    byId("stat-visits").textContent = Number(visitsResult.value.total_visits).toLocaleString("vi-VN");
    visitorCountErrorShown = false;
  } else if (visitsResult.status === "rejected") {
    byId("stat-visits").textContent = "Không tải được";
    if (!visitorCountErrorShown) {
      showToast(`Không tải được lượt truy cập: ${visitsResult.reason.message}`, true);
      visitorCountErrorShown = true;
    }
  }
}

function getTodayVisitorCountPath() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const params = new URLSearchParams({ start: start.toISOString(), end: end.toISOString() });
  return `/admin/reports/visitor-count?${params}`;
}

async function refreshVisitorCount() {
  try {
    const result = await request(getTodayVisitorCountPath());
    byId("stat-visits").textContent = Number(result.total_visits).toLocaleString("vi-VN");
    visitorCountErrorShown = false;
  } catch (error) {
    byId("stat-visits").textContent = "Không tải được";
    if (!visitorCountErrorShown) {
      showToast(`Không tải được lượt truy cập: ${error.message}`, true);
      visitorCountErrorShown = true;
    }
  }
}

async function loadPublicPois() {
  try {
    const result = await request("/pois?limit=100&language=vi");
    poiItems = result.items || [];
    if (byId("section-monitor").classList.contains("active")) loadHeatmap();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadPoiPage() {
  if (!hasPermission("poi:read")) return;
  try {
    const result = await request(`/admin/pois?limit=${poiPageSize}&skip=${(poiPage - 1) * poiPageSize}`);
    poiTotal = result.total;
    const items = result.items || [];
    byId("poi-total").textContent = `${poiTotal} điểm tham quan`;
    byId("poi-page-label").textContent = `Trang ${poiPage} / ${Math.max(1, Math.ceil(poiTotal / poiPageSize))}`;
    byId("poi-prev").disabled = poiPage <= 1;
    byId("poi-next").disabled = poiPage * poiPageSize >= poiTotal;
    byId("poi-table").innerHTML = items.length ? items.map((poi) => {
      const image = poi.image_url
        ? `<img class="poi-thumb" src="${escapeHtml(new URL(poi.image_url, API_ORIGIN).href)}" alt="" loading="lazy">`
        : `<span class="poi-thumb placeholder">⌖</span>`;
      const actions = [
        hasPermission("poi:write") ? `<button class="button button-outline button-small" data-poi-edit="${escapeHtml(poi.id)}">Sửa</button><button class="button button-danger button-small" data-poi-delete="${escapeHtml(poi.id)}">Xóa</button>` : "",
        !hasPermission("poi:write") && hasPermission("content:write") ? `<button class="button button-outline button-small" data-poi-audio="${escapeHtml(poi.id)}">Âm thanh</button>` : "",
      ].join("");
      return `<tr><td><div class="poi-name">${image}<span>${escapeHtml(poi.name)}</span></div></td><td>${escapeHtml(poi.category)}</td><td>${Number(poi.coordinates.latitude).toFixed(5)}, ${Number(poi.coordinates.longitude).toFixed(5)}</td><td><span class="status-pill ${poi.is_active ? "active" : ""}">${poi.is_active ? "Đang hoạt động" : "Tạm ẩn"}</span></td><td><div class="row-actions">${actions}</div></td></tr>`;
    }).join("") : `<tr><td colspan="5" class="empty-message">Chưa có điểm tham quan.</td></tr>`;
  } catch (error) {
    showToast(error.message, true);
  }
}

function bindControls() {
  byId("logout-button").addEventListener("click", logout);
  byId("poi-refresh").addEventListener("click", loadPoiPage);
  byId("poi-prev").addEventListener("click", () => { poiPage = Math.max(1, poiPage - 1); loadPoiPage(); });
  byId("poi-next").addEventListener("click", () => { poiPage += 1; loadPoiPage(); });
  byId("add-poi-button").addEventListener("click", () => openPoiDialog());
  byId("poi-table").addEventListener("click", handlePoiTableAction);
  byId("poi-form").addEventListener("submit", savePoi);
  byId("poi-form").addEventListener("click", handleAudioAction);
  byId("poi-form").elements.content_vi.addEventListener("input", scheduleTranslationPreview);
  byId("poi-form").elements.name.addEventListener("input", scheduleFieldTranslationPreview);
  byId("poi-form").elements.category.addEventListener("input", scheduleFieldTranslationPreview);
  byId("poi-image-select-button").addEventListener("click", () => {
    if (!byId("poi-image-select-button").disabled) byId("poi-image-file").click();
  });
  byId("poi-image-file").addEventListener("change", selectPoiImage);
  byId("poi-image-upload-button").addEventListener("click", uploadPoiImage);
  byId("poi-form").elements.image_url.addEventListener("input", (event) => updatePoiImagePreview(event.target.value));
  byId("poi-map-search-button").addEventListener("click", searchPoiMap);
  byId("poi-map-search-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchPoiMap();
    }
  });
  byId("poi-map-search-results").addEventListener("click", selectPoiMapSearchResult);
  byId("heatmap-refresh").addEventListener("click", loadHeatmap);
  byId("report-form").addEventListener("submit", (event) => { event.preventDefault(); loadReport(); });
  document.querySelector(".export-actions").addEventListener("click", exportReport);
  byId("add-admin-button").addEventListener("click", () => openAdminDialog());
  byId("admin-form").addEventListener("submit", saveAdmin);
  byId("admin-table").addEventListener("click", handleAdminAction);
  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => byId(button.dataset.closeDialog).close());
  });
  byId("poi-dialog").addEventListener("close", () => {
    pickerMap?.remove();
    pickerMap = null;
    pickerMarker = null;
    byId("poi-map-search-input").value = "";
    byId("poi-map-search-status").textContent = "";
    byId("poi-map-search-results").replaceChildren();
    byId("picker-map-status").textContent = "";
  });
}

async function logout() {
  try {
    await request("/auth/logout", { method: "POST" });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    websocket?.close();
    window.location.replace("login.html");
  }
}

function openPoiDialog(poi = null) {
  const canEditPoi = hasPermission("poi:write");
  if (!canEditPoi && (!poi || !hasPermission("content:write"))) return;
  const form = byId("poi-form");
  form.reset();
  form.elements.poi_id.value = poi?.id || "";
  window.clearTimeout(translationPreviewTimer);
  translationPreviewRequest += 1;
  lastPreviewedSource = "";
  byId("poi-translation-status").textContent =
    "Khi ngừng nhập tiếng Việt, bản dịch English, 日本語, 한국어 và 中文 sẽ tự động cập nhật và thay thế bản dịch cũ.";
  form.elements.name.value = poi?.name || "";
  form.elements.category.value = poi?.category || "";
  window.clearTimeout(fieldTranslationTimer);
  fieldTranslationRequest += 1;
  poiNameTranslations = poi?.name_translations || {};
  poiCategoryTranslations = poi?.category_translations || {};
  lastFieldTranslationSource = poi
    ? `${form.elements.name.value.trim()}|${form.elements.category.value.trim()}`
    : "";
  byId("poi-field-translation-status").textContent =
    "Tên và danh mục tiếng Việt sẽ được tự động dịch sang English, 日本語, 한국어 và 中文.";
  renderFieldTranslations();
  form.elements.image_url.value = poi?.image_url || "";
  const imageFileInput = byId("poi-image-file");
  const imageSelectButton = byId("poi-image-select-button");
  const imageUploadButton = byId("poi-image-upload-button");
  imageFileInput.value = "";
  imageFileInput.disabled = !canEditPoi;
  imageSelectButton.disabled = !canEditPoi;
  imageUploadButton.disabled = true;
  byId("poi-image-upload-status").textContent = "";
  updatePoiImagePreview(poi?.image_url || "");
  form.elements.latitude.value = poi?.coordinates.latitude ?? 10.7769;
  form.elements.longitude.value = poi?.coordinates.longitude ?? 106.7009;
  form.elements.geofence_radius_m.value = poi?.geofence_radius_m ?? 50;
  for (const [language] of LANGUAGES) form.elements[`content_${language}`].value = poi?.content?.[language] || "";
  form.elements.is_active.checked = poi?.is_active ?? true;
  form.querySelectorAll("[name]").forEach((field) => {
    if (field.name !== "poi_id") field.disabled = !canEditPoi;
  });
  byId("poi-dialog-title").textContent = poi
    ? "Chỉnh sửa điểm tham quan"
    : "Thêm điểm tham quan";
  byId("poi-save-button").textContent = poi
    ? "Lưu thay đổi"
    : "Lưu điểm tham quan";
  byId("poi-audio-tools").hidden = !poi || !hasPermission("content:write");
  byId("poi-audio-list").innerHTML = poi ? renderAudioRows(poi) : "";
  byId("poi-save-button").hidden = !canEditPoi;
  byId("poi-dialog").showModal();
  window.setTimeout(() => initializePickerMap(poi), 80);
}

function initializePickerMap(poi) {
  const status = byId("picker-map-status");
  if (!window.L) {
    status.textContent = "Không tải được thư viện bản đồ. Kiểm tra kết nối Internet.";
    showToast(status.textContent, true);
    return;
  }
  const latitude = Number(byId("poi-form").elements.latitude.value);
  const longitude = Number(byId("poi-form").elements.longitude.value);
  const position = [latitude, longitude];
  pickerMap = L.map(byId("poi-picker-map")).setView(position, poi ? 17 : 15);
  addBaseMapLayers(pickerMap);
  pickerMarker = L.marker(position, { draggable: true, title: "Vị trí điểm tham quan" }).addTo(pickerMap);
  pickerMarker.on("dragend", () => setPoiCoordinates(pickerMarker.getLatLng()));
  pickerMap.on("click", (event) => {
    pickerMarker.setLatLng(event.latlng);
    setPoiCoordinates(event.latlng);
  });
  status.textContent = "Bấm lên bản đồ hoặc kéo ghim để đặt vị trí chính xác.";
  window.setTimeout(() => pickerMap?.invalidateSize(), 100);
}

function formatGeocoderLabel(query, details) {
  const name = details.name || details.display_name || details.city || query;
  const parts = [
    details.street,
    details.house_number,
    details.suburb,
    details.district,
    details.city,
    details.state,
    details.country,
  ].filter((value) => Boolean(value) && String(value).trim() !== "");
  return [name, ...parts.filter((value, index, values) => values.indexOf(value) === index)].join(", ");
}

async function fetchPlaceSearchResults(query) {
  const providers = [
    {
      name: "Photon",
      buildUrl: () => {
        const url = new URL("https://photon.komoot.io/api/");
        url.search = new URLSearchParams({
          q: query,
          limit: "5",
          lat: "16.0471",
          lon: "108.2068",
          bbox: "102.14,8.18,109.47,23.39",
        }).toString();
        return url;
      },
      parse: (payload) => {
        const places = Array.isArray(payload?.features) ? payload.features : [];
        return places.map((place) => {
          const [longitude, latitude] = (place.geometry?.coordinates || []).map(Number);
          const details = place.properties || {};
          return {
            latitude,
            longitude,
            label: formatGeocoderLabel(query, details),
          };
        }).filter((place) => Number.isFinite(place.latitude) && Number.isFinite(place.longitude));
      },
    },
    {
      name: "Nominatim",
      buildUrl: () => {
        const url = new URL("https://nominatim.openstreetmap.org/search");
        url.search = new URLSearchParams({
          q: query,
          format: "jsonv2",
          limit: "5",
          addressdetails: "1",
          bounded: "1",
          viewbox: "102.14,23.39,109.47,8.18",
          "accept-language": "vi",
        }).toString();
        return url;
      },
      parse: (payload) => {
        const places = Array.isArray(payload) ? payload : [];
        return places.map((place) => {
          const latitude = Number(place.lat);
          const longitude = Number(place.lon);
          const address = place.address || {};
          return {
            latitude,
            longitude,
            label: formatGeocoderLabel(query, {
              name: place.name || place.display_name,
              street: address.road || address.pedestrian,
              house_number: address.house_number,
              suburb: address.suburb || address.neighbourhood,
              district: address.county || address.city_district || address.municipality,
              city: address.city || address.town || address.village,
              state: address.state,
              country: address.country,
            }),
          };
        }).filter((place) => Number.isFinite(place.latitude) && Number.isFinite(place.longitude));
      },
    },
  ];

  for (const provider of providers) {
    try {
      const url = provider.buildUrl();
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
        mode: "cors",
      });
      if (!response.ok) {
        if (response.status === 429) continue;
        continue;
      }
      const payload = await response.json();
      const places = provider.parse(payload);
      if (places.length) return { provider: provider.name, places };
    } catch (error) {
      continue;
    }
  }

  return { provider: "", places: [] };
}

async function searchPoiMap() {
  const input = byId("poi-map-search-input");
  const button = byId("poi-map-search-button");
  const status = byId("poi-map-search-status");
  const results = byId("poi-map-search-results");
  const query = input.value.trim();
  results.replaceChildren();
  if (query.length < 3) {
    status.textContent = "Nhập ít nhất 3 ký tự để tìm địa điểm.";
    return;
  }
  if (!navigator.onLine) {
    status.textContent = "Không có kết nối mạng để tìm địa điểm.";
    return;
  }

  button.disabled = true;
  status.textContent = "Đang tìm địa điểm...";
  try {
    const wait = Math.max(0, 1100 - (Date.now() - lastMapSearchAt));
    if (wait) await new Promise((resolve) => window.setTimeout(resolve, wait));
    lastMapSearchAt = Date.now();
    const searchResult = await fetchPlaceSearchResults(query);
    const places = searchResult.places;
    if (!places.length) {
      status.textContent = "Không tìm thấy địa điểm. Hãy thử tên khác hoặc chọn vị trí trực tiếp trên bản đồ.";
      return;
    }
    status.textContent = `Tìm thấy ${places.length} kết quả${searchResult.provider ? ` từ ${searchResult.provider}` : ""}. Chọn một địa điểm để chuyển ghim.`;
    for (const place of places) {
      const result = document.createElement("button");
      result.type = "button";
      result.className = "map-search-result";
      result.dataset.latitude = String(place.latitude);
      result.dataset.longitude = String(place.longitude);
      result.textContent = place.label || query;
      results.append(result);
    }
    if (results.childElementCount) results.scrollIntoView({ block: "nearest" });
    else status.textContent = "Kết quả tìm kiếm không có tọa độ hợp lệ.";
  } catch (error) {
    status.textContent = error instanceof TypeError
      ? "Không kết nối được dịch vụ tìm kiếm. Kiểm tra mạng rồi thử lại."
      : error.message || "Không tìm được địa điểm lúc này. Vui lòng thử lại.";
  } finally {
    button.disabled = false;
  }
}

function selectPoiMapSearchResult(event) {
  const result = event.target.closest(".map-search-result");
  if (!result || !pickerMap || !pickerMarker) return;
  const position = {
    lat: Number(result.dataset.latitude),
    lng: Number(result.dataset.longitude),
  };
  if (!Number.isFinite(position.lat) || !Number.isFinite(position.lng)) return;
  pickerMarker.setLatLng(position);
  pickerMap.setView(position, 17);
  setPoiCoordinates(position);
  byId("picker-map-status").textContent = "Đã chọn vị trí tìm được. Có thể kéo ghim để tinh chỉnh.";
}

function setPoiCoordinates(point) {
  const form = byId("poi-form");
  const latitude = typeof point.lat === "function" ? point.lat() : point.lat;
  const longitude = typeof point.lng === "function" ? point.lng() : point.lng;
  form.elements.latitude.value = Number(latitude).toFixed(6);
  form.elements.longitude.value = Number(longitude).toFixed(6);
}

function updatePoiImagePreview(imageUrl) {
  const preview = byId("poi-image-preview");
  const normalizedUrl = String(imageUrl || "").trim();
  preview.hidden = !normalizedUrl;
  preview.removeAttribute("src");
  if (poiImagePreviewObjectUrl && normalizedUrl !== poiImagePreviewObjectUrl) {
    URL.revokeObjectURL(poiImagePreviewObjectUrl);
    poiImagePreviewObjectUrl = undefined;
  }
  if (!normalizedUrl) return;
  try {
    preview.src = new URL(normalizedUrl, API_ORIGIN).href;
  } catch {
    preview.hidden = true;
  }
}

function selectPoiImage(event) {
  const input = event.currentTarget;
  const file = input.files[0];
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) {
    const message = "Ảnh không được vượt quá 10 MB.";
    byId("poi-image-upload-status").textContent = message;
    showToast(message, true);
    input.value = "";
    return;
  }
  if (file.type && !["image/jpeg", "image/png", "image/webp", "image/gif"].includes(file.type)) {
    const message = "Chỉ hỗ trợ ảnh JPG, PNG, WebP hoặc GIF.";
    byId("poi-image-upload-status").textContent = message;
    showToast(message, true);
    input.value = "";
    return;
  }
  if (poiImagePreviewObjectUrl) URL.revokeObjectURL(poiImagePreviewObjectUrl);
  poiImagePreviewObjectUrl = URL.createObjectURL(file);
  updatePoiImagePreview(poiImagePreviewObjectUrl);
  byId("poi-image-upload-button").disabled = false;
  byId("poi-image-upload-status").textContent =
    `Đã chọn "${file.name}". Nhấn “Tải ảnh lên” để gửi ảnh lên máy chủ.`;
}

async function uploadPoiImage() {
  const input = byId("poi-image-file");
  const file = input.files[0];
  if (!file) {
    byId("poi-image-upload-status").textContent = "Hãy chọn ảnh từ máy trước.";
    return;
  }
  const button = byId("poi-image-select-button");
  const uploadButton = byId("poi-image-upload-button");
  const originalText = button.textContent;
  button.disabled = true;
  uploadButton.disabled = true;
  uploadButton.textContent = "Đang tải ảnh...";
  byId("poi-image-upload-status").textContent = `Đang tải "${file.name}" lên máy chủ...`;
  try {
    const body = new FormData();
    body.append("file", file);
    const result = await request("/admin/images/upload", { method: "POST", body });
    byId("poi-form").elements.image_url.value = new URL(result.image_url, API_ORIGIN).href;
    updatePoiImagePreview(result.image_url);
    const message = "Tải ảnh thành công. Nhấn “Lưu điểm tham quan” để ảnh xuất hiện trên app.";
    byId("poi-image-upload-status").textContent = message;
    input.value = "";
    showToast(message);
  } catch (error) {
    byId("poi-image-upload-status").textContent = `Tải ảnh thất bại: ${error.message}`;
    showToast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = originalText;
    uploadButton.textContent = "Tải ảnh lên";
    uploadButton.disabled = !input.files[0];
  }
}

function fieldTranslationSource() {
  const form = byId("poi-form");
  return `${form.elements.name.value.trim()}|${form.elements.category.value.trim()}`;
}

function renderFieldTranslations() {
  const container = byId("poi-field-translations");
  const disabled = hasPermission("poi:write") ? "" : " disabled";
  container.innerHTML = LANGUAGES
    .filter(([language]) => language !== "vi")
    .map(([language, label]) => {
      const name = escapeHtml(poiNameTranslations[language] || "");
      const category = escapeHtml(poiCategoryTranslations[language] || "");
      return `<div class="field-translation-row">
        <strong>${escapeHtml(label)}</strong>
        <input data-field="name" data-language="${language}" placeholder="Tên hiển thị" maxlength="200" value="${name}"${disabled}>
        <input data-field="category" data-language="${language}" placeholder="Danh mục" maxlength="100" value="${category}"${disabled}>
      </div>`;
    })
    .join("");
}

function collectFieldTranslations() {
  const names = {};
  const categories = {};
  byId("poi-field-translations").querySelectorAll("input[data-field]").forEach((input) => {
    const value = input.value.trim();
    if (!value) return;
    if (input.dataset.field === "name") names[input.dataset.language] = value;
    else categories[input.dataset.language] = value;
  });
  return { names, categories };
}

async function previewTranslations(text) {
  const targetLanguages = LANGUAGES
    .map(([language]) => language)
    .filter((language) => language !== "vi");
  const result = await request("/admin/translations/preview", {
    method: "POST",
    body: JSON.stringify({ text, target_languages: targetLanguages }),
  });
  return result.translations || {};
}

function scheduleFieldTranslationPreview() {
  window.clearTimeout(fieldTranslationTimer);
  const status = byId("poi-field-translation-status");
  const name = byId("poi-form").elements.name.value.trim();
  if (!name) {
    status.textContent = "Nhập tên điểm tham quan tiếng Việt để tự động dịch tên và danh mục.";
    return;
  }
  if (fieldTranslationSource() === lastFieldTranslationSource) return;
  status.textContent = "Đang chờ bạn nhập xong để cập nhật bản dịch tên và danh mục...";
  fieldTranslationTimer = window.setTimeout(generateFieldTranslations, 1800);
}

async function generateFieldTranslations() {
  const form = byId("poi-form");
  const name = form.elements.name.value.trim();
  const category = form.elements.category.value.trim();
  const source = fieldTranslationSource();
  if (!name) return;
  const requestId = ++fieldTranslationRequest;
  const status = byId("poi-field-translation-status");
  status.textContent = "Đang dịch tên và danh mục...";
  try {
    const [nameTranslations, categoryTranslations] = await Promise.all([
      previewTranslations(name),
      category ? previewTranslations(category) : Promise.resolve({}),
    ]);
    if (requestId !== fieldTranslationRequest || fieldTranslationSource() !== source) return;
    poiNameTranslations = nameTranslations;
    poiCategoryTranslations = categoryTranslations;
    lastFieldTranslationSource = source;
    renderFieldTranslations();
    status.textContent = "Đã tự động dịch tên và danh mục cho 4 ngôn ngữ. Bạn có thể chỉnh sửa nội dung chi tiết bên dưới.";
  } catch (error) {
    if (requestId !== fieldTranslationRequest) return;
    status.textContent = `Không dịch được tên/danh mục: ${error.message}`;
  }
}

function scheduleTranslationPreview(event) {
  window.clearTimeout(translationPreviewTimer);
  const sourceText = event.currentTarget.value.trim();
  const status = byId("poi-translation-status");
  if (sourceText.length < 8) {
    status.textContent = "Nhập nội dung tiếng Việt; bản dịch sẽ tự sinh sau khi ngừng nhập.";
    return;
  }
  if (sourceText === lastPreviewedSource) return;
  status.textContent = "Đang chờ bạn nhập xong để cập nhật bản dịch...";
  translationPreviewTimer = window.setTimeout(
    () => generateTranslationPreview(sourceText),
    1800,
  );
}

async function generateTranslationPreview(sourceText) {
  const requestId = ++translationPreviewRequest;
  const status = byId("poi-translation-status");
  const targetLanguages = LANGUAGES
    .map(([language]) => language)
    .filter((language) => language !== "vi");
  status.textContent = "Đang dịch và cập nhật English, 日本語, 한국어 và 中文...";
  try {
    const result = await request("/admin/translations/preview", {
      method: "POST",
      body: JSON.stringify({ text: sourceText, target_languages: targetLanguages }),
    });
    const sourceField = byId("poi-form").elements.content_vi;
    if (requestId !== translationPreviewRequest || sourceField.value.trim() !== sourceText) return;
    const translations = result.translations || {};
    let updated = 0;
    for (const [language] of LANGUAGES) {
      if (language === "vi") continue;
      const field = byId("poi-form").elements[`content_${language}`];
      if (translations[language]) {
        field.value = translations[language];
        updated += 1;
      }
    }
    lastPreviewedSource = sourceText;
    status.textContent = updated === targetLanguages.length
      ? "Đã tự động cập nhật bản dịch cho cả 4 ngôn ngữ. Bạn có thể chỉnh sửa trước khi lưu."
      : "Đã cập nhật một phần bản dịch; hãy kiểm tra các ngôn ngữ chưa có nội dung.";
  } catch (error) {
    if (requestId !== translationPreviewRequest) return;
    status.textContent = `Không tạo được bản dịch tự động: ${error.message}`;
  }
}

async function savePoi(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  const content = {};
  for (const [language] of LANGUAGES) {
    const text = String(values.get(`content_${language}`) || "").trim();
    if (text) content[language] = text;
  }
  if (!content.vi) {
    showToast("Vui lòng nhập nội dung tiếng Việt cho điểm tham quan.", true);
    return;
  }
  if (hasPermission("poi:write") && String(values.get("name")).trim()) {
    const hasManualTranslations = Object.keys(collectFieldTranslations().names).length > 0;
    if (fieldTranslationSource() !== lastFieldTranslationSource && !hasManualTranslations) {
      window.clearTimeout(fieldTranslationTimer);
      await generateFieldTranslations();
    }
  }
  const fieldTranslations = collectFieldTranslations();
  const payload = {
    name: String(values.get("name")).trim(),
    category: String(values.get("category")).trim(),
    image_url: String(values.get("image_url") || "").trim() || null,
    coordinates: { latitude: Number(values.get("latitude")), longitude: Number(values.get("longitude")) },
    geofence_radius_m: Number(values.get("geofence_radius_m")),
    content,
    is_active: form.elements.is_active.checked,
    name_translations: fieldTranslations.names,
    category_translations: fieldTranslations.categories,
  };
  const poiId = form.elements.poi_id.value;
  const button = byId("poi-save-button");
  button.disabled = true;
  try {
    await request(poiId ? `/admin/pois/${encodeURIComponent(poiId)}` : "/admin/pois", {
      method: poiId ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    byId("poi-dialog").close();
    showToast(poiId ? "Đã cập nhật địa điểm." : "Đã tạo điểm tham quan.");
    await loadPoiPage();
    await loadPublicPois();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function handlePoiTableAction(event) {
  const editButton = event.target.closest("[data-poi-edit]");
  const audioButton = event.target.closest("[data-poi-audio]");
  const deleteButton = event.target.closest("[data-poi-delete]");
  if (editButton || audioButton) {
    const poiId = editButton?.dataset.poiEdit || audioButton.dataset.poiAudio;
    try {
      const result = await request(`/pois/${encodeURIComponent(poiId)}?language=vi`);
      const adminData = await request(`/admin/pois?limit=100&skip=0`);
      const poi = adminData.items.find((item) => item.id === poiId) || result;
      openPoiDialog(poi);
    } catch (error) {
      showToast(error.message, true);
    }
  }
  if (deleteButton && window.confirm("Bạn có chắc muốn xóa điểm tham quan này?")) {
    try {
      await request(`/admin/pois/${encodeURIComponent(deleteButton.dataset.poiDelete)}`, { method: "DELETE" });
      showToast("Đã xóa điểm tham quan.");
      if (poiPage > 1 && (poiPage - 1) * poiPageSize >= poiTotal - 1) poiPage -= 1;
      await loadPoiPage();
      await loadPublicPois();
    } catch (error) {
      showToast(error.message, true);
    }
  }
}

function renderAudioRows(poi) {
  return LANGUAGES.map(([language, name]) => {
    const url = poi.audio?.[language];
    return `<div class="audio-row"><strong>${language.toUpperCase()}</strong>${url ? `<audio controls preload="none" src="${escapeHtml(new URL(url, API_ORIGIN).href)}"></audio>` : `<span class="muted">Chưa có audio</span>`}<button type="button" class="button button-outline button-small" data-audio-generate="${language}">Sinh AI</button><label class="button button-outline button-small">Tải MP3<input type="file" accept="audio/mpeg,.mp3" data-audio-upload="${language}" hidden></label></div>`;
  }).join("");
}

async function handleAudioAction(event) {
  const generateButton = event.target.closest("[data-audio-generate]");
  const uploadInput = event.target.closest("[data-audio-upload]");
  if (!generateButton && !uploadInput) return;
  const poiId = byId("poi-form").elements.poi_id.value;
  if (!poiId) return;
  const language = generateButton?.dataset.audioGenerate || uploadInput?.dataset.audioUpload;
  const button = generateButton || uploadInput.parentElement;
  button.disabled = true;
  const originalText = button.textContent;
  button.textContent = generateButton ? "Đang sinh..." : "Đang tải...";
  try {
    if (generateButton) {
      await request(`/admin/pois/${encodeURIComponent(poiId)}/audio/${language}/generate`, { method: "POST" });
    } else {
      const file = uploadInput.files[0];
      if (!file) return;
      if (file.size > 20 * 1024 * 1024) throw new Error("Tệp MP3 không được vượt quá 20 MB.");
      const body = new FormData();
      body.append("file", file);
      await request(`/admin/pois/${encodeURIComponent(poiId)}/audio/${language}/upload`, { method: "POST", body });
    }
    const result = await request(`/admin/pois?limit=100&skip=0`);
    const updatedPoi = result.items.find((item) => item.id === poiId);
    byId("poi-audio-list").innerHTML = renderAudioRows(updatedPoi || { audio: {} });
    showToast("Đã cập nhật âm thanh thuyết minh.");
    loadPoiPage();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

async function initializeHeatMap() {
  if (heatMap) return heatMap;
  if (!window.L) throw new Error("Không tải được thư viện bản đồ. Kiểm tra kết nối Internet.");
  heatMap = L.map(byId("heatmap-map")).setView([16.0471, 108.2068], 5);
  addBaseMapLayers(heatMap);
  window.setTimeout(() => heatMap?.invalidateSize(), 350);
  return heatMap;
}

async function loadHeatmap() {
  if (!hasPermission("heatmap:read")) return;
  try {
    const data = await request("/admin/heatmap");
    await initializeHeatMap();
    heatMap.invalidateSize();
    heatMapCircles.forEach((circle) => circle.remove());
    heatMapCircles = [];
    for (const cell of data.cells) {
      const intensity = Math.min(1, cell.count / 10);
      const circle = L.circle([cell.latitude, cell.longitude], {
        radius: 125,
        color: cell.warning ? "#ff5252" : "#ff8f00",
        opacity: 0.65,
        weight: 1,
        fillColor: cell.warning ? "#ff5252" : "#ffc107",
        fillOpacity: 0.12 + intensity * 0.3,
      }).bindPopup(`<strong>${cell.count} khách</strong>${cell.warning ? "<br>Cảnh báo đông khách" : ""}`).addTo(heatMap);
      heatMapCircles.push(circle);
    }
    if (data.cells.length && !heatMapHasAutoFitted) {
      heatMap.fitBounds(
        L.latLngBounds(data.cells.map((cell) => [cell.latitude, cell.longitude])),
        { padding: [24, 24], maxZoom: 15 },
      );
      heatMapHasAutoFitted = true;
    }
    for (const crowd of data.poi_crowds) {
      const poi = poiItems.find((item) => item.id === crowd.poi_id);
      if (!poi) continue;
      const circle = L.circleMarker([poi.coordinates.latitude, poi.coordinates.longitude], {
        radius: crowd.warning ? 10 : 8,
        color: crowd.warning ? "#ff5252" : "#ffc107",
        opacity: 0.95,
        weight: 2,
        fillColor: crowd.warning ? "#ff5252" : "#ffc107",
        fillOpacity: 0.8,
      }).bindPopup(`<strong>${escapeHtml(crowd.name)}</strong><br>${crowd.visitor_count} khách${crowd.warning ? " — QUÁ ĐÔNG" : ""}`).addTo(heatMap);
      heatMapCircles.push(circle);
    }
    const located = Number(data.located_visitors) || 0;
    byId("heatmap-map-status").textContent = located
      ? `Bản đồ đang hiển thị vị trí của ${located} khách có GPS gần đây.`
      : "Chưa có khách gửi vị trí GPS gần đây. Khách cần cho phép định vị và giữ trang thuyết minh đang mở.";
    renderPoiPresence(data.poi_crowds);
  } catch (error) {
    byId("heatmap-map-status").textContent = `Không tải được bản đồ giám sát: ${error.message}`;
    showToast(error.message, true);
  }
}

function renderPoiPresence(poiCounts = []) {
  const counts = new Map(poiCounts.map((item) => [item.poi_id, item]));
  const activePois = poiItems.filter((poi) => poi.is_active);
  byId("poi-presence-table").innerHTML = activePois.length ? activePois.map((poi) => {
    const record = counts.get(poi.id);
    const count = record?.visitor_count || 0;
    const warning = count > 50;
    return `<tr><td>${escapeHtml(poi.name)}</td><td>${count}</td><td><span class="status-pill ${warning ? "danger" : "active"}">${warning ? "Quá đông" : "Ổn định"}</span></td></tr>`;
  }).join("") : `<tr><td colspan="3" class="empty-message">Chưa có điểm tham quan.</td></tr>`;
}

function setReportDates() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);
  byId("report-end").value = end.toISOString().slice(0, 10);
  byId("report-start").value = start.toISOString().slice(0, 10);
}

async function loadReport() {
  const start = byId("report-start").value;
  const end = byId("report-end").value;
  if (start > end) {
    showToast("Ngày bắt đầu không được sau ngày kết thúc.", true);
    return;
  }
  try {
    const report = await request(`/admin/reports?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`);
    byId("report-total").textContent = report.total_visits;
    byId("language-report").innerHTML = report.by_language.map((item) =>
      `<tr><td>${escapeHtml(item.language.toUpperCase())}</td><td>${item.visits}</td></tr>`
    ).join("") || `<tr><td colspan="2" class="empty-message">Không có dữ liệu.</td></tr>`;
    drawReportCharts(report);
  } catch (error) {
    byId("report-total").textContent = "—";
    showToast(error.message, true);
  }
}

function drawReportCharts(report) {
  const chartOptions = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: "#b9b9b9" }, grid: { color: "#292929" } },
      y: { beginAtZero: true, ticks: { precision: 0, color: "#b9b9b9" }, grid: { color: "#292929" } },
    },
  };
  poiChart?.destroy();
  dayChart?.destroy();
  poiChart = new Chart(byId("poi-chart"), {
    type: "bar",
    data: { labels: report.by_poi.map((item) => item.name), datasets: [{ data: report.by_poi.map((item) => item.visits), backgroundColor: "#ffc107", borderRadius: 5 }] },
    options: chartOptions,
  });
  dayChart = new Chart(byId("day-chart"), {
    type: "line",
    data: { labels: report.by_day.map((item) => item.date), datasets: [{ data: report.by_day.map((item) => item.visits), borderColor: "#ffc107", backgroundColor: "#ffc10722", fill: true, tension: .3 }] },
    options: chartOptions,
  });
}

async function exportReport(event) {
  const button = event.target.closest("[data-format]");
  if (!button) return;
  const start = byId("report-start").value;
  const end = byId("report-end").value;
  if (!start || !end || start > end) {
    showToast("Hãy chọn khoảng ngày hợp lệ trước khi xuất báo cáo.", true);
    return;
  }
  const format = button.dataset.format;
  try {
    const response = await fetch(`${API_ROOT}/admin/reports/export?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}&format=${format}`, { credentials: "include" });
    if (!response.ok) {
      let detail;
      try { detail = (await response.json()).detail; } catch { detail = null; }
      throw new Error(localizeDetail(detail, response.status));
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `bao-cao-${start}-${end}.${format}`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadAdmins() {
  if (currentAdmin.role !== "super_admin") return;
  try {
    const result = await request("/admin/admins?limit=500");
    byId("admin-table").innerHTML = result.items.map((admin) => {
      const disabled = admin.id === currentAdmin.id;
      return `<tr><td><strong>${escapeHtml(admin.display_name)}</strong><br><small class="muted">${escapeHtml(admin.email)}</small></td><td>${escapeHtml(ROLE_LABELS[admin.role] || admin.role)}</td><td><span class="status-pill ${admin.is_active ? "active" : "danger"}">${admin.is_active ? "Hoạt động" : "Đã khóa"}</span></td><td><div class="row-actions"><button class="button button-outline button-small" data-admin-edit="${escapeHtml(admin.id)}">Sửa</button><button class="button button-outline button-small" data-admin-toggle="${escapeHtml(admin.id)}" data-active="${admin.is_active}">${admin.is_active ? "Khóa" : "Mở khóa"}</button><button class="button button-outline button-small" data-admin-password="${escapeHtml(admin.id)}">Mật khẩu</button><button class="button button-danger button-small" data-admin-delete="${escapeHtml(admin.id)}" ${disabled ? "disabled title='Không thể tự xóa tài khoản'" : ""}>Xóa</button></div></td></tr>`;
    }).join("");
  } catch (error) {
    showToast(error.message, true);
  }
}

function openAdminDialog(admin = null) {
  const form = byId("admin-form");
  form.reset();
  form.elements.admin_id.value = admin?.id || "";
  form.elements.email.value = admin?.email || "";
  form.elements.display_name.value = admin?.display_name || "";
  form.elements.role.value = admin?.role || "area_operator";
  form.elements.password.required = !admin;
  form.elements.password.value = "";
  byId("admin-dialog-title").textContent = admin ? "Chỉnh sửa tài khoản" : "Thêm tài khoản";
  byId("new-password-field").hidden = Boolean(admin);
  byId("admin-dialog").showModal();
}

async function saveAdmin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  const adminId = form.elements.admin_id.value;
  const payload = {
    email: String(values.get("email")).trim(),
    display_name: String(values.get("display_name")).trim(),
    role: values.get("role"),
  };
  if (values.get("password")) payload.password = values.get("password");
  try {
    await request(adminId ? `/admin/admins/${encodeURIComponent(adminId)}` : "/admin/admins", {
      method: adminId ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });
    byId("admin-dialog").close();
    showToast(adminId ? "Đã cập nhật tài khoản." : "Đã tạo tài khoản.");
    await loadAdmins();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function handleAdminAction(event) {
  const edit = event.target.closest("[data-admin-edit]");
  const toggle = event.target.closest("[data-admin-toggle]");
  const password = event.target.closest("[data-admin-password]");
  const remove = event.target.closest("[data-admin-delete]");
  const adminId = edit?.dataset.adminEdit || toggle?.dataset.adminToggle || password?.dataset.adminPassword || remove?.dataset.adminDelete;
  if (!adminId) return;
  let row;
  try {
    row = (await request("/admin/admins?limit=500")).items.find((admin) => admin.id === adminId);
  } catch (error) {
    showToast(error.message, true);
    return;
  }
  if (!row) return;
  if (edit) return openAdminDialog(row);
  if (toggle) {
    try {
      await request(`/admin/admins/${encodeURIComponent(adminId)}`, { method: "PATCH", body: JSON.stringify({ is_active: toggle.dataset.active !== "true" }) });
      showToast(toggle.dataset.active === "true" ? "Đã khóa tài khoản." : "Đã mở khóa tài khoản.");
      await loadAdmins();
    } catch (error) { showToast(error.message, true); }
  }
  if (password) {
    const newPassword = window.prompt("Nhập mật khẩu mới (ít nhất 12 ký tự):");
    if (newPassword === null) return;
    try {
      await request(`/admin/admins/${encodeURIComponent(adminId)}`, { method: "PATCH", body: JSON.stringify({ password: newPassword }) });
      showToast("Đã đổi mật khẩu.");
    } catch (error) { showToast(error.message, true); }
  }
  if (remove && window.confirm(`Xóa tài khoản ${row.email}?`)) {
    try {
      await request(`/admin/admins/${encodeURIComponent(adminId)}`, { method: "DELETE" });
      showToast("Đã xóa tài khoản.");
      await loadAdmins();
    } catch (error) { showToast(error.message, true); }
  }
}

function connectAdminSocket() {
  if (!hasPermission("visitor:read")) return;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  websocket = new WebSocket(`${protocol}//${API_ORIGIN_URL.host}/ws/admin`);
  websocket.addEventListener("open", () => setConnection(true, "Đang kết nối WebSocket trực tiếp"));
  websocket.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type !== "presence") return;
      const onlineCount = Number(data.online) || 0;
      if (lastOnlineCount !== null && onlineCount > lastOnlineCount) {
        refreshVisitorCount();
      }
      lastOnlineCount = onlineCount;
      byId("stat-online").textContent = data.online;
      byId("monitor-online").textContent = data.online;
      const counts = new Map((data.poi_counts || []).map((item) => [item.poi_id, item]));
      renderPoiPresence([...counts.values()]);
      setConnection(true, `${data.online*2} khách đang trực tuyến`);
      if (byId("section-monitor").classList.contains("active")) loadHeatmap();
    } catch {
      setConnection(false, "Không thể đọc dữ liệu WebSocket");
    }
  });
  websocket.addEventListener("close", () => {
    setConnection(false, "Mất kết nối — đang thử kết nối lại");
    window.clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(connectAdminSocket, 2000);
  });
  websocket.addEventListener("error", () => websocket.close());
}

window.addEventListener("pagehide", () => {
  window.clearTimeout(reconnectTimer);
  window.clearInterval(visitorCountRefreshTimer);
  websocket?.close();
});

initialize();
