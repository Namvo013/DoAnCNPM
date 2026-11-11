const API_ORIGIN_URL = new URL(window.location.origin);
if (API_ORIGIN_URL.port === "5500") API_ORIGIN_URL.port = "8000";
const API_ORIGIN = API_ORIGIN_URL.origin;
const API_BASE = `${API_ORIGIN}/api`;
const LANGUAGES = new Set(["vi", "en", "ja", "ko", "zh"]);
const UI_TEXT = {
  vi: {
    pageTitle: "Thuyết minh theo vị trí",
    pageDescription: "Thuyết minh du lịch tự động theo vị trí GPS.",
    tagline: "HƯỚNG DẪN ÂM THANH · GPS",
    gateHeading: "Chọn ngôn ngữ",
    gateCopy: "Hãy chọn ngôn ngữ thuyết minh trước khi bắt đầu khám phá.",
    languageLabel: "Ngôn ngữ thuyết minh",
    languageLabelShort: "Ngôn ngữ",
    exitTour: "Quay lại màn hình chính",
    languageSelectAria: "Chọn ngôn ngữ thuyết minh",
    continue: "Tiếp tục",
    brand: "THUYẾT MINH",
    brandSubtitle: "HƯỚNG DẪN THEO VỊ TRÍ",
    introHeading: "Hành trình di sản trong tầm tay",
    introCopy: "Khám phá câu chuyện đằng sau mỗi điểm đến với hướng dẫn viên ảo tự động kích hoạt qua GPS. Chỉ cần cấp quyền vị trí, âm thanh thuyết minh sẽ tự động vang lên ngay khi bạn bước tới. Hãy bắt đầu hành trình cảm xúc của riêng bạn ngay bây giờ.",
    start: "◎　Bắt đầu hành trình",
    privacy: "Vị trí chỉ được dùng để xác định điểm tham quan gần bạn trong lúc mở hành trình.",
    mapEyebrow: "BẢN ĐỒ HÀNH TRÌNH",
    mapTitle: "Điểm tham quan quanh bạn",
    mapAria: "Bản đồ các điểm tham quan",
    mapGps: "Bật GPS để tìm vị trí",
    gpsOff: "Chưa bật định vị",
    poiNearYou: "ĐIỂM GẦN BẠN",
    ready: "Sẵn sàng khám phá",
    locationPrompt: "Cho phép truy cập vị trí để thiết bị tự nhận biết khi bạn đến gần một điểm tham quan.",
    playNarration: "▶　Phát thuyết minh",
    inJourney: "TRONG HÀNH TRÌNH",
    poiListTitle: "Điểm tham quan",
    loadingPois: "Đang tải danh sách điểm tham quan...",
    footer: "Đến gần một điểm để tự phát thuyết minh, hoặc chạm nút Nghe để chủ động phát bất cứ lúc nào.",
    connectionError: "Không kết nối được máy chủ thuyết minh. Hãy kiểm tra backend đang chạy.",
    accessDenied: "Không có quyền truy cập dữ liệu chuyến tham quan.",
    loadTourError: "Không tải được dữ liệu chuyến tham quan. Vui lòng thử lại.",
    poiCount: "{count} điểm",
    nearby: "Bạn đang ở gần",
    radius: "Bán kính {meters} m",
    listenTo: "Nghe thuyết minh {name}",
    listen: "▶ Nghe",
    noAudio: "Chưa có audio",
    mapLibraryError: "Không tải được thư viện bản đồ. Kiểm tra kết nối Internet.",
    loadingMapPois: "Đang tải điểm tham quan...",
    mapPoiCount: "{count} điểm trên bản đồ",
    noPois: "Chưa có điểm tham quan",
    noPoisOnMap: "Bản đồ đã sẵn sàng. Chưa có POI hoạt động để hiển thị; thêm điểm tham quan trong trang quản trị.",
    poiCategory: "Điểm tham quan",
    yourLocation: "Vị trí của bạn",
    selectedDistance: "{meters} m · vùng {radius} m",
    selectedRadius: "Bán kính geofence {meters} m",
    onlineNoGps: "Đang trực tuyến · chưa bật định vị",
    gpsActive: "Định vị đang hoạt động",
    reconnecting: "Đang nối lại kết nối...",
    continueExploring: "Tiếp tục khám phá",
    outsideGeofence: "Chưa ở trong vùng thuyết minh của điểm nào. Khi đến gần một POI, nội dung sẽ tự phát.",
    distanceToPoi: "{meters} m đến điểm",
    currentDistance: "Bạn đang cách điểm khoảng {meters} m · vùng {radius} m",
    noAudioForLanguage: "Chưa có audio thuyết minh cho ngôn ngữ này.",
    tapToPlay: "▶　Chạm để phát thuyết minh",
    tapToHear: "Chạm nút phát để nghe {name}.",
    trackingPosition: "Đang theo dõi vị trí",
    locationPermission: "Bạn chưa cho phép truy cập vị trí. Hãy bật quyền định vị của trình duyệt.",
    locationUnavailable: "Không xác định được vị trí. Hãy kiểm tra GPS và thử lại.",
    locationTimeout: "Định vị phản hồi quá chậm. Hãy thử lại ở nơi có tín hiệu tốt hơn.",
    locationError: "Không thể lấy vị trí hiện tại.",
    gpsUnsupported: "Trình duyệt này không hỗ trợ định vị GPS.",
    startingGps: "Đang bật định vị...",
    waitingGps: "Đang chờ vị trí GPS...",
    retry: "◎　Thử lại",
    playFailed: "Không phát được audio của {name}. Hãy chạm nút phát trên trình phát.",
    mapZoomIn: "Phóng to",
    mapZoomOut: "Thu nhỏ",
    recenterMap: "◎　Về vị trí của tôi",
    streetMap: "Đường phố",
    satelliteMap: "Vệ tinh",
  },
  en: {
    pageTitle: "Location-based Audio Guide",
    pageDescription: "Automatic GPS-based travel narration.",
    tagline: "AUDIO GUIDE · GPS",
    gateHeading: "Choose a language",
    gateCopy: "Choose your narration language before you start exploring.",
    languageLabel: "Narration language",
    languageLabelShort: "Language",
    exitTour: "Back to Home",
    languageSelectAria: "Choose narration language",
    continue: "Continue",
    brand: "AUDIO GUIDE",
    brandSubtitle: "LOCATION-BASED GUIDE",
    introHeading: "Your Heritage Journey Awaits",
    introCopy: "Unveil the stories behind every destination with a smart AI guide that activates automatically via GPS. Simply allow location access, and the narration will come to life as you arrive. Start your personal voyage of discovery now.",
    start: "◎　Start your journey",
    privacy: "Your location is used only to find nearby points while your journey is active.",
    mapEyebrow: "JOURNEY MAP",
    mapTitle: "Attractions near you",
    mapAria: "Map of attractions",
    mapGps: "Enable GPS to find your location",
    gpsOff: "Location is off",
    poiNearYou: "NEARBY POINT",
    ready: "Ready to explore",
    locationPrompt: "Allow location access so your device can detect nearby attractions.",
    playNarration: "▶　Play narration",
    inJourney: "YOUR JOURNEY",
    poiListTitle: "Attractions",
    loadingPois: "Loading attractions...",
    footer: "Approach a point for automatic narration, or tap Listen to play it anytime.",
    connectionError: "Could not connect to the audio guide server. Check that the backend is running.",
    accessDenied: "You do not have access to this tour data.",
    loadTourError: "Could not load tour data. Please try again.",
    poiCount: "{count} points",
    nearby: "Nearby",
    radius: "Radius: {meters} m",
    listenTo: "Listen to narration for {name}",
    listen: "▶ Listen",
    noAudio: "No audio yet",
    mapLibraryError: "Could not load the map. Check your Internet connection.",
    loadingMapPois: "Loading attractions...",
    mapPoiCount: "{count} points on map",
    noPois: "No attractions yet",
    noPoisOnMap: "The map is ready, but there are no active attractions to show. Add attractions in the admin page.",
    poiCategory: "Attraction",
    yourLocation: "Your location",
    selectedDistance: "{meters} m · radius {radius} m",
    selectedRadius: "Geofence radius: {meters} m",
    onlineNoGps: "Online · location is off",
    gpsActive: "Location is active",
    reconnecting: "Reconnecting...",
    continueExploring: "Keep exploring",
    outsideGeofence: "You are not near an attraction yet. Narration will play automatically when you approach one.",
    distanceToPoi: "{meters} m to point",
    currentDistance: "About {meters} m away · radius {radius} m",
    noAudioForLanguage: "No narration is available in this language.",
    tapToPlay: "▶　Tap to play narration",
    tapToHear: "Tap play to hear {name}.",
    trackingPosition: "Tracking your location",
    locationPermission: "Location access was denied. Enable location permission in your browser.",
    locationUnavailable: "Your location could not be determined. Check GPS and try again.",
    locationTimeout: "Location lookup timed out. Try again where the signal is stronger.",
    locationError: "Could not get your current location.",
    gpsUnsupported: "This browser does not support GPS location.",
    startingGps: "Enabling location...",
    waitingGps: "Waiting for GPS...",
    retry: "◎　Try again",
    playFailed: "Could not play audio for {name}. Tap play on the audio player.",
    mapZoomIn: "Zoom in",
    mapZoomOut: "Zoom out",
    recenterMap: "◎　My location",
    streetMap: "Streets",
    satelliteMap: "Satellite",
  },
  ja: {
    pageTitle: "位置情報オーディオガイド",
    pageDescription: "GPS位置情報を利用した観光音声ガイド。",
    tagline: "音声ガイド · GPS",
    gateHeading: "言語を選択",
    gateCopy: "探索を始める前に、ガイドの言語を選択してください。",
    languageLabel: "ガイドの言語",
    languageLabelShort: "言語",
    exitTour: "ホームに戻る",
    languageSelectAria: "ガイドの言語を選択",
    continue: "続行",
    brand: "音声ガイド",
    brandSubtitle: "位置情報ガイド",
    introHeading: "手のひらに広がる遺産の旅",
    introCopy: "GPSで自動起動するスマートAIガイドとともに、各スポットに秘められた物語を解き明かしましょう。位置情報を許可するだけで、到着に合わせて音声ガイドが流れ始めます。あなただけの感動的な旅を今すぐ始めましょう。",
    start: "◎　探索を開始",
    privacy: "位置情報は、探索中に近くの観光スポットを検出するためだけに使用されます。",
    mapEyebrow: "ルートマップ",
    mapTitle: "近くの観光スポット",
    mapAria: "観光スポットの地図",
    mapGps: "GPSを有効にして現在地を確認",
    gpsOff: "位置情報はオフです",
    poiNearYou: "近くのスポット",
    ready: "探索の準備完了",
    locationPrompt: "位置情報を許可すると、近くの観光スポットを検出できます。",
    playNarration: "▶　ガイドを再生",
    inJourney: "ルート内",
    poiListTitle: "観光スポット",
    loadingPois: "スポットを読み込み中...",
    footer: "スポットに近づくと音声が自動再生されます。「聴く」をタップしていつでも再生できます。",
    connectionError: "ガイドサーバーに接続できません。バックエンドの状態を確認してください。",
    accessDenied: "このツアーデータにアクセスできません。",
    loadTourError: "ツアーデータを読み込めません。もう一度お試しください。",
    poiCount: "{count}か所",
    nearby: "近くにいます",
    radius: "半径 {meters} m",
    listenTo: "{name}のガイドを再生",
    listen: "▶ 聴く",
    noAudio: "音声なし",
    mapLibraryError: "地図を読み込めません。インターネット接続を確認してください。",
    loadingMapPois: "観光スポットを読み込み中...",
    mapPoiCount: "地図上に{count}か所",
    noPois: "観光スポットがありません",
    noPoisOnMap: "地図の準備ができました。有効なスポットがありません。管理ページから追加してください。",
    poiCategory: "観光スポット",
    yourLocation: "現在地",
    selectedDistance: "{meters} m · 範囲 {radius} m",
    selectedRadius: "ジオフェンス半径 {meters} m",
    onlineNoGps: "オンライン · 位置情報はオフ",
    gpsActive: "位置情報を取得中",
    reconnecting: "再接続中...",
    continueExploring: "探索を続ける",
    outsideGeofence: "近くにスポットはありません。スポットに近づくと音声ガイドが自動再生されます。",
    distanceToPoi: "スポットまで{meters} m",
    currentDistance: "スポットまで約{meters} m · 範囲 {radius} m",
    noAudioForLanguage: "この言語の音声ガイドはありません。",
    tapToPlay: "▶　タップしてガイドを再生",
    tapToHear: "{name}を再生するには再生ボタンをタップしてください。",
    trackingPosition: "現在地を追跡中",
    locationPermission: "位置情報が許可されていません。ブラウザーの設定で許可してください。",
    locationUnavailable: "現在地を取得できません。GPSを確認して再試行してください。",
    locationTimeout: "位置情報の取得がタイムアウトしました。電波の良い場所で再試行してください。",
    locationError: "現在地を取得できません。",
    gpsUnsupported: "このブラウザーはGPS位置情報に対応していません。",
    startingGps: "位置情報を有効にしています...",
    waitingGps: "GPSを待っています...",
    retry: "◎　再試行",
    playFailed: "{name}の音声を再生できません。プレーヤーの再生ボタンをタップしてください。",
    mapZoomIn: "拡大",
    mapZoomOut: "縮小",
    recenterMap: "◎　現在地",
    streetMap: "道路地図",
    satelliteMap: "衛星写真",
  },
  ko: {
    pageTitle: "위치 기반 오디오 가이드",
    pageDescription: "GPS 위치 기반 자동 관광 안내.",
    tagline: "오디오 가이드 · GPS",
    gateHeading: "언어 선택",
    gateCopy: "탐험을 시작하기 전에 안내 언어를 선택하세요.",
    languageLabel: "안내 언어",
    languageLabelShort: "언어",
    exitTour: "홈으로 돌아가기",
    languageSelectAria: "안내 언어 선택",
    continue: "계속",
    brand: "오디오 가이드",
    brandSubtitle: "위치 기반 안내",
    introHeading: "내 손안의 유산 여행",
    introCopy: "GPS를 통해 자동으로 활성화되는 스마트 AI 가이드와 함께 각 목적지에 숨겨진 이야기를 만나보세요. 위치 권한을 허용하면 도착하는 순간 생생한 음성 안내가 시작됩니다. 지금 바로 당신만의 특별한 여정을 시작하세요.",
    start: "◎　여행 시작",
    privacy: "위치 정보는 여행 중 주변 관광지를 찾는 용도로만 사용됩니다.",
    mapEyebrow: "여행 지도",
    mapTitle: "주변 관광지",
    mapAria: "관광지 지도",
    mapGps: "GPS를 켜서 위치 찾기",
    gpsOff: "위치 정보 꺼짐",
    poiNearYou: "주변 지점",
    ready: "탐험 준비 완료",
    locationPrompt: "위치 접근을 허용하면 주변 관광지를 자동으로 찾습니다.",
    playNarration: "▶　안내 재생",
    inJourney: "여행 경로",
    poiListTitle: "관광지",
    loadingPois: "관광지 목록을 불러오는 중...",
    footer: "지점에 가까워지면 안내가 자동 재생됩니다. 언제든 듣기를 눌러 재생할 수 있습니다.",
    connectionError: "안내 서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.",
    accessDenied: "이 여행 데이터에 접근할 수 없습니다.",
    loadTourError: "여행 데이터를 불러올 수 없습니다. 다시 시도하세요.",
    poiCount: "{count}곳",
    nearby: "근처에 있습니다",
    radius: "반경 {meters} m",
    listenTo: "{name} 안내 듣기",
    listen: "▶ 듣기",
    noAudio: "오디오 없음",
    mapLibraryError: "지도를 불러올 수 없습니다. 인터넷 연결을 확인하세요.",
    loadingMapPois: "관광지를 불러오는 중...",
    mapPoiCount: "지도에 {count}곳",
    noPois: "관광지가 없습니다",
    noPoisOnMap: "지도가 준비되었습니다. 표시할 활성 관광지가 없습니다. 관리자 페이지에서 추가하세요.",
    poiCategory: "관광지",
    yourLocation: "내 위치",
    selectedDistance: "{meters} m · 반경 {radius} m",
    selectedRadius: "지오펜스 반경 {meters} m",
    onlineNoGps: "온라인 · 위치 정보 꺼짐",
    gpsActive: "위치 정보 사용 중",
    reconnecting: "다시 연결하는 중...",
    continueExploring: "계속 둘러보기",
    outsideGeofence: "주변에 관광지가 없습니다. 지점에 가까워지면 안내가 자동 재생됩니다.",
    distanceToPoi: "지점까지 {meters} m",
    currentDistance: "약 {meters} m 거리 · 반경 {radius} m",
    noAudioForLanguage: "이 언어의 오디오 안내가 없습니다.",
    tapToPlay: "▶　눌러서 안내 재생",
    tapToHear: "{name}을(를) 들으려면 재생 버튼을 누르세요.",
    trackingPosition: "위치 추적 중",
    locationPermission: "위치 접근이 거부되었습니다. 브라우저 설정에서 허용하세요.",
    locationUnavailable: "위치를 확인할 수 없습니다. GPS를 확인하고 다시 시도하세요.",
    locationTimeout: "위치 확인 시간이 초과되었습니다. 신호가 좋은 곳에서 다시 시도하세요.",
    locationError: "현재 위치를 가져올 수 없습니다.",
    gpsUnsupported: "이 브라우저는 GPS 위치 기능을 지원하지 않습니다.",
    startingGps: "위치 정보 사용 설정 중...",
    waitingGps: "GPS를 기다리는 중...",
    retry: "◎　다시 시도",
    playFailed: "{name} 오디오를 재생할 수 없습니다. 오디오 플레이어의 재생 버튼을 누르세요.",
    mapZoomIn: "확대",
    mapZoomOut: "축소",
    recenterMap: "◎　내 위치",
    streetMap: "일반 지도",
    satelliteMap: "위성 지도",
  },
  zh: {
    pageTitle: "位置语音导览",
    pageDescription: "基于 GPS 位置的自动旅游讲解。",
    tagline: "语音导览 · GPS",
    gateHeading: "选择语言",
    gateCopy: "开始探索前，请先选择导览语言。",
    languageLabel: "导览语言",
    languageLabelShort: "语言",
    exitTour: "返回主界面",
    languageSelectAria: "选择解说语言",
    continue: "继续",
    brand: "语音导览",
    brandSubtitle: "位置导览",
    introHeading: "触手可及的文化之旅",
    introCopy: "通过GPS自动激活的智能AI导览，揭开每个目的地背后的故事。只需开启定位权限，导览语音便会在您到达时自动响起。现在就开启属于您的感性之旅吧。",
    start: "◎　开始行程",
    privacy: "行程开启期间，位置信息仅用于查找附近景点。",
    mapEyebrow: "行程地图",
    mapTitle: "附近景点",
    mapAria: "景点地图",
    mapGps: "开启 GPS 以查找位置",
    gpsOff: "定位未开启",
    poiNearYou: "附近景点",
    ready: "准备开始探索",
    locationPrompt: "允许访问位置，设备即可识别附近景点。",
    playNarration: "▶　播放讲解",
    inJourney: "行程中",
    poiListTitle: "景点",
    loadingPois: "正在加载景点列表...",
    footer: "靠近景点即可自动播放讲解，也可以随时点击“收听”手动播放。",
    connectionError: "无法连接导览服务器，请检查后端是否正在运行。",
    accessDenied: "无权访问此行程数据。",
    loadTourError: "无法加载行程数据，请重试。",
    poiCount: "{count} 个景点",
    nearby: "就在附近",
    radius: "半径 {meters} 米",
    listenTo: "收听{name}的讲解",
    listen: "▶ 收听",
    noAudio: "暂无音频",
    mapLibraryError: "无法加载地图，请检查网络连接。",
    loadingMapPois: "正在加载景点...",
    mapPoiCount: "地图上有 {count} 个景点",
    noPois: "暂无景点",
    noPoisOnMap: "地图已就绪，但没有可显示的景点。请在管理页面添加景点。",
    poiCategory: "景点",
    yourLocation: "您的位置",
    selectedDistance: "{meters} 米 · 范围 {radius} 米",
    selectedRadius: "电子围栏半径 {meters} 米",
    onlineNoGps: "在线 · 定位未开启",
    gpsActive: "定位已开启",
    reconnecting: "正在重新连接...",
    continueExploring: "继续探索",
    outsideGeofence: "附近暂无景点。靠近景点时将自动播放讲解。",
    distanceToPoi: "距离景点 {meters} 米",
    currentDistance: "距离约 {meters} 米 · 范围 {radius} 米",
    noAudioForLanguage: "此语言暂无语音讲解。",
    tapToPlay: "▶　点击播放讲解",
    tapToHear: "点击播放按钮收听{name}。",
    trackingPosition: "正在定位",
    locationPermission: "定位权限被拒绝，请在浏览器设置中允许访问位置。",
    locationUnavailable: "无法确定位置，请检查 GPS 后重试。",
    locationTimeout: "定位超时，请在信号较好的地方重试。",
    locationError: "无法获取当前位置。",
    gpsUnsupported: "此浏览器不支持 GPS 定位。",
    startingGps: "正在开启定位...",
    waitingGps: "正在等待 GPS...",
    retry: "◎　重试",
    playFailed: "无法播放{name}的音频，请点击播放器上的播放按钮。",
    mapZoomIn: "放大",
    mapZoomOut: "缩小",
    recenterMap: "◎　我的位置",
    streetMap: "街道地图",
    satelliteMap: "卫星图",
  },
};

const elements = {
  gate: document.getElementById("language-gate"),
  tourShell: document.getElementById("tour-shell"),
  initialLanguage: document.getElementById("initial-language-select"),
  enterTour: document.getElementById("enter-tour-button"),
  start: document.getElementById("start-button"),
  language: document.getElementById("language-select"),
  exitTour: document.getElementById("exit-tour-btn"),
  gpsStatus: document.getElementById("gps-status"),
  pulse: document.querySelector(".pulse-dot"),
  title: document.getElementById("poi-title"),
  image: document.getElementById("poi-image"),
  content: document.getElementById("poi-content"),
  distance: document.getElementById("distance-label"),
  audio: document.getElementById("audio-player"),
  manualPlay: document.getElementById("manual-play"),
  list: document.getElementById("poi-list"),
  count: document.getElementById("poi-count"),
  map: document.getElementById("tour-map"),
  mapStatus: document.getElementById("map-status"),
  recenterMap: document.getElementById("recenter-map"),
  mapMessage: document.getElementById("map-message"),
};

let pois = [];
let map = null;
let poiMarkers = new Map();
let poiCircles = new Map();
let userMarker = null;
let userAccuracyCircle = null;
let followUser = true;
let currentPoiId = null;
let watchId = null;
let websocket = null;
let heartbeatTimer = null;
let reconnectTimer = null;
let hasEnteredTour = false;
let currentPosition = null;
let queuedAudioPoi = null;
let selectedCardPoiId = null;
const playedPoiIds = new Set();

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function poiImageUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value, API_ORIGIN);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function getPoiContent(poi, language = uiLanguage()) {
  if (!poi.content) return "";
  const contentLanguage = poi.content_language || language;
  return poi.content[contentLanguage]
    || poi.content[language]
    || poi.content.en
    || poi.content.vi
    || "";
}

function uiLanguage() {
  const select = hasEnteredTour ? elements.language : elements.initialLanguage;
  return LANGUAGES.has(select?.value) ? select.value : "vi";
}

function text(key, values = {}, language = uiLanguage()) {
  const dictionary = UI_TEXT[language] || UI_TEXT.vi;
  const template = dictionary[key] || UI_TEXT.vi[key] || key;
  return template.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}

function localizeMapControls() {
  const language = uiLanguage();
  document.querySelectorAll(".leaflet-control-zoom-in").forEach((node) => {
    node.title = text("mapZoomIn", {}, language);
    node.setAttribute("aria-label", text("mapZoomIn", {}, language));
  });
  document.querySelectorAll(".leaflet-control-zoom-out").forEach((node) => {
    node.title = text("mapZoomOut", {}, language);
    node.setAttribute("aria-label", text("mapZoomOut", {}, language));
  });
}

function applyUiLanguage(language) {
  const dictionary = UI_TEXT[language] || UI_TEXT.vi;
  document.documentElement.lang = language;
  document.title = dictionary.pageTitle || UI_TEXT.vi.pageTitle;
  
  // Đồng bộ giá trị giữa 2 bộ chọn ngôn ngữ
  if (elements.language && elements.initialLanguage) {
    if (elements.language.value !== language) elements.language.value = language;
    if (elements.initialLanguage.value !== language) elements.initialLanguage.value = language;
  }

  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) metaDesc.content = dictionary.pageDescription || UI_TEXT.vi.pageDescription;

  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.dataset.i18n;
    if (dictionary[key]) {
      node.textContent = dictionary[key];
    } else if (UI_TEXT.vi[key]) {
      node.textContent = UI_TEXT.vi[key];
    }
  });

  if (userMarker) userMarker.setPopupContent(text("yourLocation", {}, language));

  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    const key = node.dataset.i18nAriaLabel;
    if (dictionary[key]) {
      node.setAttribute("aria-label", dictionary[key]);
    } else if (UI_TEXT.vi[key]) {
      node.setAttribute("aria-label", UI_TEXT.vi[key]);
    }
  });

  localizeMapControls();
  if (elements.mapStatus) elements.mapStatus.textContent = text("mapGps", {}, language);
  
  if (elements.gpsStatus) {
    elements.gpsStatus.textContent = hasEnteredTour
      ? websocket?.readyState === WebSocket.OPEN
        ? watchId === null ? text("onlineNoGps", {}, language) : text("gpsActive", {}, language)
        : text("reconnecting", {}, language)
      : text("gpsOff", {}, language);
  }

  if (elements.count) {
    elements.count.textContent = text("poiCount", { count: pois.length }, language);
  }

  // Cập nhật nội dung POI đang hiển thị (nếu có)
  const activePoiId = currentPoiId || selectedCardPoiId;
  if (activePoiId) {
    const activePoi = pois.find(p => p.id === activePoiId);
    if (activePoi) showPoiOnCard(activePoi);
  }

  if (!pois.length) {
    if (elements.list) {
      elements.list.innerHTML = `<p class="empty-message">${escapeHtml(text("loadingPois", {}, language))}</p>`;
    }
  } else {
    renderPoiList(lastDistances);
    // Cập nhật lại các popup trên bản đồ mà không cần render lại toàn bộ marker
    updateMapPopups(language);
  }
}

function updateMapPopups(language) {
  if (!map) return;
  poiMarkers.forEach((marker, id) => {
    const poi = pois.find(p => p.id === id);
    if (!poi) return;
    
    const imageUrl = poiImageUrl(poi.image_url);
    const description = getPoiContent(poi, language);
    const truncatedDescription = description.length > 120 
      ? description.substring(0, 117) + "..." 
      : description;

    marker.setPopupContent(
      `<div class="poi-map-popup">` +
      (imageUrl ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(poi.name)}" loading="lazy">` : "") +
      `<strong>${escapeHtml(poi.name || text("poiCategory", {}, language))}</strong>` +
      `<small>${escapeHtml(poi.category || text("poiCategory", {}, language))}</small>` +
      (truncatedDescription ? `<p>${escapeHtml(truncatedDescription)}</p>` : "") +
      `</div>`
    );
  });
}

async function getJson(path) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`);
  } catch {
    throw new Error(text("connectionError"));
  }
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error(text("accessDenied"));
    }
    throw new Error(text("loadTourError"));
  }
  return payload;
}

function selectedLanguage() {
  const params = new URLSearchParams(window.location.search);
  const language = params.get("lang") || params.get("language");
  return LANGUAGES.has(language) ? language : "vi";
}

async function loadPois() {
  const language = uiLanguage();
  const result = await getJson(`/pois?limit=100&language=${encodeURIComponent(language)}`);
  pois = result.items;
  renderPoiList(lastDistances);
  renderPoiMarkers();
  const activePoiId = currentPoiId || selectedCardPoiId;
  const selectedPoi = pois.find((poi) => poi.id === activePoiId);
  if (selectedPoi) showPoiOnCard(selectedPoi);
}

function renderPoiList(distances = new Map()) {
  elements.count.textContent = text("poiCount", { count: pois.length });
  elements.list.innerHTML = pois.length ? [...pois]
    .sort((a, b) => (distances.get(a.id) ?? Infinity) - (distances.get(b.id) ?? Infinity))
    .map((poi) => {
      const distance = distances.get(poi.id);
      const isCurrent = poi.id === currentPoiId;
      const detail = Number.isFinite(distance)
        ? distance <= poi.geofence_radius_m
          ? text("nearby")
          : `${Math.round(distance)} m`
        : text("radius", { meters: poi.geofence_radius_m });
      const hasAudio = Boolean(chooseAudio(poi));
      const imageUrl = poiImageUrl(poi.image_url);
      return `<article class="poi-card${isCurrent ? " current" : ""}${imageUrl ? " has-image" : ""}">${imageUrl ? `<img class="poi-card-image" src="${escapeHtml(imageUrl)}" alt="" loading="lazy">` : ""}<div class="poi-card-details"><strong>${escapeHtml(poi.name)}</strong><small>${escapeHtml(poi.category || text("poiCategory"))} · ${escapeHtml(detail)}</small></div><button class="poi-play-button" type="button" data-poi-id="${escapeHtml(poi.id)}" aria-label="${escapeHtml(text("listenTo", { name: poi.name }))}"${hasAudio ? "" : " disabled"}>${hasAudio ? text("listen") : text("noAudio")}</button></article>`;
    }).join("")
    : `<p class="empty-message">${escapeHtml(text("noPois"))}</p>`;
  elements.list.querySelectorAll(".poi-play-button:not(:disabled)").forEach((button) => {
    button.addEventListener("click", () => {
      const poi = pois.find((item) => item.id === button.dataset.poiId);
      if (!poi) return;
      showPoiOnCard(poi);
      playPoiNarration(poi);
    });
  });
  elements.list.querySelectorAll(".poi-card-image").forEach((image) => {
    image.addEventListener("error", () => {
      image.closest(".poi-card")?.classList.remove("has-image");
      image.remove();
    }, { once: true });
  });
}

function showMapMessage(message, isError = false) {
  elements.mapMessage.textContent = message;
  elements.mapMessage.classList.toggle("error", isError);
  elements.mapMessage.hidden = !message;
}

function initializeMap() {
  if (!elements.map) return Promise.resolve(null);
  if (map) return Promise.resolve(map);
  if (!window.L) {
    const error = new Error(text("mapLibraryError"));
    elements.mapStatus.textContent = error.message;
    showMapMessage(error.message, true);
    return Promise.resolve(null);
  }
  map = L.map(elements.map).setView([16.0471, 108.2068], 5);
  map.on("dragstart", () => {
    followUser = false;
  });
  localizeMapControls();
  const streets = L.tileLayer("https://tile.openstreetmap.de/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    },
  );
  L.control.layers({
    [text("streetMap")]: streets,
    [text("satelliteMap")]: satellite,
  }).addTo(map);
  elements.mapStatus.textContent = text("loadingMapPois");
  renderPoiMarkers();
  window.setTimeout(() => map?.invalidateSize(), 100);
  return Promise.resolve(map);
}

function renderPoiMarkers() {
  if (!map) return;
  poiMarkers.forEach((marker) => marker.remove());
  poiCircles.forEach((circle) => circle.remove());
  poiMarkers.clear();
  poiCircles.clear();
  const bounds = L.latLngBounds([]);
  let count = 0;
  for (const poi of pois) {
    const latitude = Number(poi.coordinates?.latitude);
    const longitude = Number(poi.coordinates?.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) continue;
    const position = [latitude, longitude];
    bounds.extend(position);
    count += 1;
    const marker = L.circleMarker(position, {
      radius: 9,
      color: "#0B0B0B",
      weight: 3,
      fillColor: "#FFC107",
      fillOpacity: 1,
    }).addTo(map);
    const imageUrl = poiImageUrl(poi.image_url);
    const description = getPoiContent(poi);
    const truncatedDescription = description.length > 120 
      ? description.substring(0, 117) + "..." 
      : description;

    marker.bindPopup(
      `<div class="poi-map-popup">` +
      (imageUrl ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(poi.name)}" loading="lazy">` : "") +
      `<strong>${escapeHtml(poi.name || text("poiCategory"))}</strong>` +
      `<small>${escapeHtml(poi.category || text("poiCategory"))}</small>` +
      (truncatedDescription ? `<p>${escapeHtml(truncatedDescription)}</p>` : "") +
      `</div>`,
      { maxWidth: 220 }
    );
    marker.on("click", () => {
      showPoiOnCard(poi);
      playPoiNarration(poi);
    });
    poiMarkers.set(poi.id, marker);
    const circle = L.circle(position, {
      radius: Number(poi.geofence_radius_m) || 30,
      color: "#FFC107",
      weight: 1,
      opacity: 0.65,
      fillColor: "#FFC107",
      fillOpacity: 0.08,
      interactive: false,
    }).addTo(map);
    poiCircles.set(poi.id, circle);
  }
  elements.mapStatus.textContent = count
    ? text("mapPoiCount", { count })
    : text("noPois");
  showMapMessage(count
    ? ""
    : text("noPoisOnMap"));
  if (count === 1) map.setView(bounds.getCenter(), 15);
  else if (count > 1) map.fitBounds(bounds, { padding: [28, 28] });
  if (currentPosition) updateUserMapMarker(currentPosition);
  window.setTimeout(() => map?.invalidateSize(), 100);
}

function showPoiOnCard(poi) {
  selectedCardPoiId = poi.id;
  const distance = lastDistances.get(poi.id);
  elements.title.textContent = poi.name;
  const imageUrl = poiImageUrl(poi.image_url);
  elements.image.hidden = !imageUrl;
  elements.image.removeAttribute("src");
  if (imageUrl) {
    elements.image.src = imageUrl;
    elements.image.alt = `Ảnh ${poi.name || "điểm tham quan"}`;
  } else {
    elements.image.alt = "";
  }
  
  elements.content.textContent = getPoiContent(poi);
  
  elements.distance.textContent = Number.isFinite(distance)
    ? text("selectedDistance", { meters: Math.round(distance), radius: poi.geofence_radius_m })
    : text("selectedRadius", { meters: poi.geofence_radius_m });
  
  poiMarkers.get(poi.id)?.openPopup();
  
  // Tự động cuộn xuống thẻ thông tin trên thiết bị di động
  if (window.innerWidth <= 760) {
    elements.tourShell.querySelector(".now-playing").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function updateUserMapMarker(position, accuracy = 0) {
  if (!map || !position) return;
  const firstFix = !userMarker;
  if (!userMarker) {
    userMarker = L.circleMarker([position.latitude, position.longitude], {
      radius: 8,
      color: "#FFFFFF",
      weight: 3,
      fillColor: "#348CFF",
      fillOpacity: 1,
    }).addTo(map).bindPopup(text("yourLocation"));
    map.setView([position.latitude, position.longitude], 16);
  } else userMarker.setLatLng([position.latitude, position.longitude]);
    elements.recenterMap.disabled = false;
    if (!firstFix && followUser && !map.getBounds().pad(-0.2).contains([position.latitude, position.longitude])) {
      map.panTo([position.latitude, position.longitude], { animate: true, duration: 0.5 });
    }
  if (accuracy > 0) {
    if (!userAccuracyCircle) {
      userAccuracyCircle = L.circle([position.latitude, position.longitude], {
        radius: accuracy,
        color: "#348CFF",
        weight: 1,
        opacity: 0.55,
        fillColor: "#348CFF",
        fillOpacity: 0.08,
        interactive: false,
      }).addTo(map);
    } else {
      userAccuracyCircle.setLatLng([position.latitude, position.longitude]);
      userAccuracyCircle.setRadius(accuracy);
    }
  }
}

function recenterMapOnUser() {
  if (!map || !currentPosition) return;
  followUser = true;
  map.setView(
    [currentPosition.latitude, currentPosition.longitude],
    Math.max(map.getZoom(), 16),
    { animate: true },
  );
}

function distanceMeters(first, second) {
  if (window.turf) {
    return turf.distance(
      turf.point([first.longitude, first.latitude]),
      turf.point([second.longitude, second.latitude]),
      { units: "kilometers" },
    ) * 1000;
  }
  const radians = (degrees) => degrees * Math.PI / 180;
  const lat1 = radians(first.latitude);
  const lat2 = radians(second.latitude);
  const deltaLat = lat2 - lat1;
  const deltaLon = radians(second.longitude - first.longitude);
  const a = Math.sin(deltaLat / 2) ** 2
    + Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
  return 6_371_008.8 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function chooseAudio(poi) {
  const audio = poi.audio || {};
  for (const language of [elements.language.value, "en", "vi"]) {
    if (audio[language]) return { language, url: audio[language] };
  }
  return null;
}

function connectVisitorSocket() {
  if (!hasEnteredTour) return;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${API_ORIGIN_URL.host}/ws/tourist?language=${encodeURIComponent(elements.language.value)}`);
  websocket = socket;
  socket.addEventListener("open", () => {
    if (websocket !== socket) return;
    elements.gpsStatus.textContent = watchId === null
      ? text("onlineNoGps")
      : text("gpsActive");
    elements.pulse.classList.add("active");
    sendHeartbeat();
  });
  socket.addEventListener("close", () => {
    if (websocket !== socket) return;
    websocket = null;
    elements.pulse.classList.remove("active");
    if (!hasEnteredTour) return;
    elements.gpsStatus.textContent = text("reconnecting");
    reconnectTimer = window.setTimeout(connectVisitorSocket, 2000);
  });
  socket.addEventListener("error", () => socket.close());
}

function sendHeartbeat() {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
  const heartbeat = {
    type: "heartbeat",
    poi_id: currentPoiId,
    language: elements.language.value,
  };
  if (currentPosition) {
    heartbeat.latitude = currentPosition.latitude;
    heartbeat.longitude = currentPosition.longitude;
  }
  websocket.send(JSON.stringify(heartbeat));
}

function setCurrentPoi(poi, distance) {
  if (poi && poi.id === currentPoiId) {
    elements.distance.textContent = text("distanceToPoi", { meters: Math.round(distance) });
    return;
  }
  const previousPoiId = currentPoiId;
  currentPoiId = poi?.id || null;
  sendHeartbeat();
  if (previousPoiId && previousPoiId === queuedAudioPoi) {
    elements.audio.pause();
    elements.audio.hidden = true;
    elements.manualPlay.hidden = true;
    queuedAudioPoi = null;
  }
  if (!poi) {
    if (previousPoiId) poiMarkers.get(previousPoiId)?.closePopup();
    selectedCardPoiId = null;
    elements.title.textContent = text("continueExploring");
    elements.content.textContent = text("outsideGeofence");
    elements.image.hidden = true;
    elements.image.removeAttribute("src");
    elements.image.alt = "";
    elements.distance.textContent = "";
    renderPoiList(lastDistances);
    return;
  }

  elements.title.textContent = poi.name;
  showPoiOnCard(poi);
  const activeLanguage = poi.content_language || elements.language.value;
  elements.content.textContent = poi.content?.[activeLanguage]
    || poi.content?.[elements.language.value]
    || poi.content?.en
    || poi.content?.vi
    || "";
  elements.distance.textContent = text("currentDistance", {
    meters: Math.round(distance),
    radius: poi.geofence_radius_m,
  });
  renderPoiList(lastDistances);

  if (playedPoiIds.has(poi.id)) return;
  if (!chooseAudio(poi)) {
    elements.content.textContent += `\n\n${text("noAudioForLanguage")}`;
    return;
  }
  playedPoiIds.add(poi.id);
  playPoiAudio(poi, true);
}

function playPoiAudio(poi, automatic) {
  const audio = chooseAudio(poi);
  if (!audio) {
    if (automatic) elements.content.textContent += `\n\n${text("noAudioForLanguage")}`;
    return;
  }
  queuedAudioPoi = poi.id;
  elements.audio.src = new URL(audio.url, API_ORIGIN).href;
  elements.audio.hidden = false;
  elements.audio.load();
  elements.audio.play().then(() => {
    elements.manualPlay.hidden = true;
  }).catch(() => {
    elements.manualPlay.hidden = false;
    elements.manualPlay.textContent = text("tapToPlay");
    if (!automatic) elements.gpsStatus.textContent = text("tapToHear", { name: poi.name });
  });
}

// Phát thuyết minh khi du khách chủ động chạm vào địa danh trên bản đồ.
function playPoiNarration(poi) {
  if (!chooseAudio(poi)) {
    elements.gpsStatus.textContent = text("noAudioForLanguage");
    return;
  }
  // Đánh dấu đã nghe để không tự phát lại khi bước vào vùng geofence.
  playedPoiIds.add(poi.id);
  playPoiAudio(poi, false);
}

let lastDistances = new Map();

function updatePosition(position) {
  currentPosition = {
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
  };
  updateUserMapMarker(currentPosition, position.coords.accuracy);
  elements.mapStatus.textContent = text("trackingPosition");
  lastDistances = new Map(pois.map((poi) => [
    poi.id,
    distanceMeters(currentPosition, {
      latitude: poi.coordinates.latitude,
      longitude: poi.coordinates.longitude,
    }),
  ]));
  const nearest = pois
    .map((poi) => ({ poi, distance: lastDistances.get(poi.id) }))
    .filter(({ poi, distance }) => distance <= poi.geofence_radius_m)
    .sort((first, second) => first.distance - second.distance)[0];
  setCurrentPoi(nearest?.poi || null, nearest?.distance ?? Infinity);
  renderPoiList(lastDistances);
  sendHeartbeat();
}

function handlePositionError(error) {
  const messages = {
    1: text("locationPermission"),
    2: text("locationUnavailable"),
    3: text("locationTimeout"),
  };
  elements.gpsStatus.textContent = messages[error.code] || text("locationError");
  // Hết thời gian chờ tín hiệu chính xác nhưng vẫn đang theo dõi và đã có vị trí thô:
  // không đặt lại nút, để GPS tiếp tục dò và tự cập nhật khi bắt được tín hiệu.
  if (error.code === 3 && watchId !== null && currentPosition) return;
  elements.start.disabled = false;
  elements.start.textContent = text("retry");
}

// Lấy nhanh vị trí thô (dựa trên mạng, không cần khóa vệ tinh) để hiển thị ngay,
// trong khi GPS chính xác cao vẫn đang được làm nóng.
function requestQuickPosition() {
  navigator.geolocation.getCurrentPosition(
    updatePosition,
    () => {},
    { enableHighAccuracy: false, timeout: 6000, maximumAge: 60000 },
  );
}

async function startTour() {
  if (!navigator.geolocation) {
    elements.gpsStatus.textContent = text("gpsUnsupported");
    return;
  }
  elements.start.disabled = true;
  elements.start.textContent = text("startingGps");
  elements.gpsStatus.textContent = text("waitingGps");
  // Gọi định vị ngay, chạy song song với việc tải bản đồ và dữ liệu điểm tham quan.
  requestQuickPosition();
  try {
    await initializeMap();
    await loadPois();
    elements.start.textContent = text("gpsActive");
    watchId = navigator.geolocation.watchPosition(
      updatePosition,
      handlePositionError,
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
    );
  } catch (error) {
    elements.gpsStatus.textContent = error.message;
    elements.list.innerHTML = `<p class="empty-message">${escapeHtml(error.message)}</p>`;
    elements.start.disabled = false;
    elements.start.textContent = text("retry");
  }
}

async function enterTour() {
  if (hasEnteredTour) return;
  hasEnteredTour = true;
  elements.language.value = elements.initialLanguage.value;
  applyUiLanguage(elements.language.value);
  elements.gate.hidden = true;
  elements.tourShell.hidden = false;

  const url = new URL(window.location.href);
  url.searchParams.delete("lang");
  url.searchParams.set("language", elements.language.value);
  window.history.replaceState({}, "", url);

  initializeMap();
  connectVisitorSocket();
  heartbeatTimer = window.setInterval(sendHeartbeat, 15000);
  try {
    await loadPois();
  } catch (error) {
    elements.gpsStatus.textContent = error.message;
    elements.list.innerHTML = `<p class="empty-message">${escapeHtml(error.message)}</p>`;
  }

}

elements.initialLanguage.value = selectedLanguage();
elements.enterTour.addEventListener("click", enterTour);
elements.start.addEventListener("click", startTour);
elements.recenterMap.addEventListener("click", recenterMapOnUser);
elements.manualPlay.addEventListener("click", () => {
  const poi = pois.find((item) => item.id === queuedAudioPoi);
  if (!poi) return;
  elements.audio.play().then(() => {
    elements.manualPlay.hidden = true;
  }).catch(() => {
    elements.gpsStatus.textContent = text("playFailed", { name: poi.name });
  });
});
elements.language.addEventListener("change", () => {
  const newLang = elements.language.value;
  
  const url = new URL(window.location.href);
  url.searchParams.delete("lang");
  url.searchParams.set("language", newLang);
  window.history.replaceState({}, "", url);
  
  applyUiLanguage(newLang);
  sendHeartbeat();
  
  // Hot-swap audio if currently playing
  if (queuedAudioPoi) {
    const poi = pois.find(p => p.id === queuedAudioPoi);
    if (poi) playPoiAudio(poi, false);
  }

  loadPois().catch((error) => {
    if (elements.gpsStatus) elements.gpsStatus.textContent = error.message;
  });
});

elements.initialLanguage.addEventListener("change", () => {
  const newLang = elements.initialLanguage.value;
  applyUiLanguage(newLang);
});

elements.exitTour?.addEventListener("click", () => {
  hasEnteredTour = false;
  elements.tourShell.hidden = true;
  elements.gate.hidden = false;
  applyUiLanguage(elements.initialLanguage.value);
});

window.addEventListener("pagehide", () => {
  hasEnteredTour = false;
  window.clearInterval(heartbeatTimer);
  window.clearTimeout(reconnectTimer);
  if (watchId !== null) window.clearWatch(watchId);
  websocket?.close();
});

applyUiLanguage(elements.initialLanguage.value);
