# Hệ thống Thuyết minh Du lịch Đa ngôn ngữ

Backend FastAPI và trang Admin Dashboard HTML/CSS/JavaScript thuần. REST API dùng prefix `/api`, tài liệu tại `http://localhost:8000/docs`.

## Chạy backend trên Windows

Yêu cầu Python 3.10+, SQL Server và Redis đang chạy; SQL Server ODBC Driver 18 cần được cài trên máy. Tạo database `CNPM` trong SQL Server trước khi chạy. Mở PowerShell tại thư mục dự án:

```powershell
Set-Location .\backend-api
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env
```

Dán secret vừa tạo vào `JWT_SECRET` trong `.env`, đặt `ADMIN_SEED_PASSWORD` dài ít nhất 12 ký tự, và kiểm tra `DATABASE_URL`/`REDIS_URL`. Cấu hình mẫu dùng Windows Integrated Authentication tới SQL Server local; nếu dùng SQL login, sửa connection string và mã hóa ký tự đặc biệt trong username/password. Cài dependency, tạo super admin ban đầu và chạy API:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m app.seed_admin
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API chạy ở `http://localhost:8000`. Kiểm tra `http://localhost:8000/api/health` hoặc mở Swagger `/docs`. Có thể đặt `GEMINI_API_KEY` để bật dịch Gemini. `COOKIE_SECURE=true` chỉ dùng khi triển khai HTTPS.

Khi khởi động, backend tự tạo các bảng nếu database chưa có schema. Bảng `visitors` lưu mỗi phiên khách và là bảng cha của `visits` cùng `visitor_locations`; Auth/monolith tự bổ sung các khóa ngoại này và tạo bản ghi visitor cho dữ liệu cũ trước khi áp dụng quan hệ. `report_exports` ghi lại tài khoản, khoảng ngày, định dạng và thời điểm mỗi lần xuất báo cáo; dữ liệu báo cáo vẫn được tổng hợp từ `visits`. Với SQL Server, Auth/monolith cũng tự chuyển `pois.name` và `pois.category` sang `NVARCHAR` nếu các cột hiện tại vẫn là `VARCHAR`, giúp lưu tiếng Việt có dấu cho dữ liệu mới. Việc chuyển kiểu giữ nguyên dữ liệu đọc được, nhưng các ký tự đã bị thay thành `?` trước đó cần nhập lại. `DATABASE_URL` có thể trỏ tới SQL Server khác; không commit connection string chứa mật khẩu.

### Chạy thử không cần SQL Server/Redis

Để xem thử đăng nhập/dashboard trên máy cá nhân mà chưa cài SQL Server và Redis, cài dependencies dev rồi đặt `ENVIRONMENT=development`, `DEMO_MODE=true`, `ADMIN_SEED_EMAIL` thành email thử nghiệm và `ADMIN_SEED_PASSWORD` thành mật khẩu riêng trong `.env`. Khởi động API như trên; chế độ demo tự tạo tài khoản khi chạy và dùng SQLite/Redis trong bộ nhớ, nên dữ liệu mất khi dừng server. Chỉ dùng cho máy local; không bật `DEMO_MODE` trong môi trường triển khai.

## Mở Admin Dashboard và trang khách

Backend tự phục vụ giao diện web. Sau khi chạy backend, mở:

- Admin: `http://localhost:8000/login.html`
- Trang khách chính: `http://localhost:8000/tourist-pwa/tour.html`
- QR truy cập khách: `http://localhost:8000/access-qr`
- API health: `http://localhost:8000/api/health`
- Swagger: `http://localhost:8000/docs`

Đăng nhập bằng tài khoản super admin được cấu hình trong `.env` và tạo bằng lệnh seed; không dùng tài khoản/mật khẩu mẫu trong tài liệu. Admin và trang khách chính dùng cùng backend nên không cần chạy frontend riêng.

Giao diện khách thử nghiệm có thêm mục **Ẩm thực** tại `http://localhost:8000/experimental-tourist/`. Chọn “Ẩm thực”, bật GPS và tìm trong bán kính 500 m–3 km để xem nhà hàng/quán ăn OpenStreetMap gần bạn, khoảng cách và nút chỉ đường. Tính năng cần Internet và quyền vị trí; tọa độ được gửi tới Overpass API qua HTTPS để truy vấn dữ liệu công khai, dữ liệu có thể thiếu hoặc chưa cập nhật. Khi dùng tunnel HTTPS trên điện thoại, mở đường dẫn `/experimental-tourist/` trên cùng tên miền tunnel. Trợ lý AI và Nhóm trong giao diện này hiện vẫn đang phát triển. Trang khách chính vẫn ở `/tourist-pwa/tour.html`.

Tất cả bản đồ dùng Leaflet với tile OpenStreetMap, không cần API key hoặc billing. Giữ nguyên ghi công OpenStreetMap trên bản đồ và tuân thủ chính sách tile; dịch vụ tile công cộng phù hợp cho thử nghiệm/lưu lượng vừa phải, không được bảo đảm SLA. Trong hộp thoại thêm POI, có thể tìm địa chỉ/địa danh ở Việt Nam; kết quả từ Photon/OpenStreetMap sẽ chuyển ghim và điền tọa độ vào biểu mẫu. Khách được tính trực tuyến ngay khi kết nối, không cần bật GPS. Trang khách chính hỗ trợ tiếng Việt, Anh, Nhật, Hàn và Trung; nội dung/audio POI sử dụng bản dịch đã xuất bản, có dự phòng sang ngôn ngữ sẵn có. Khi vào geofence, audio đã xuất bản tự phát. Mỗi điểm trong danh sách cũng có nút Nghe để khách chủ động phát audio dù chưa đến gần. Nếu trình duyệt chặn tự phát audio, khách chạm nút phát được hiển thị. Trên điện thoại ngoài mạng localhost, cần HTTPS để GPS được trình duyệt cho phép.

Nếu cần chạy frontend riêng để phát triển, mở PowerShell thứ hai:

```powershell
Set-Location .\admin-dashboard
python -m http.server 5500 --bind 0.0.0.0
```

Sau đó dùng `http://localhost:5500/login.html` hoặc `http://localhost:5500/tourist-pwa/tour.html`. Không chạy `http.server` trên cổng 8000 khi Uvicorn đang dùng cổng đó. Cookie đăng nhập là HttpOnly; dashboard gửi request với `credentials: "include"` và không lưu token trong localStorage/sessionStorage. Leaflet, OpenStreetMap tiles, Turf.js và Chart.js được tải ngoài; cần kết nối Internet để tải thư viện và bản đồ.

## Kiểm thử

Từ thư mục dự án:

```powershell
.\backend-api\.venv\Scripts\python.exe -m pytest -q .\backend-api\tests
```

Test dùng SQLite tạm và `fakeredis`, không cần SQL Server/Redis đang chạy. Gemini và Edge TTS được kiểm thử qua mock/fake, không gọi dịch vụ thật.

### CI tự động

GitHub Actions tự cài backend cùng dependencies kiểm thử, chạy toàn bộ pytest và build Docker image khi có push, pull request hoặc chạy thủ công từ tab **Actions**. Workflow ở `.github/workflows/backend-ci.yml`.

### Chạy thử kiến trúc microservice

Backend có thể chạy theo bốn tiến trình: API Gateway, Auth, POI/Nội dung và Presence. Gateway giữ các URL API hiện tại cho frontend rồi gọi Auth/POI/Presence qua HTTP hoặc WebSocket. API báo cáo vẫn chạy trên Gateway và đọc dữ liệu Visit trong SQL Server; không có Analytics Service riêng. Các service dùng `INTERNAL_SERVICE_TOKEN` để từ chối request nghiệp vụ không đi qua gateway.

#### Chạy nhanh trên Windows, không cần Docker

Đảm bảo SQL Server Express `CNPM`, Redis và `backend-api\.venv` đã sẵn sàng; `.env` phải cấu hình SQL Server/Redis và `DEMO_MODE=false`. Mở PowerShell tại thư mục dự án, chạy:

```powershell
.\start-microservices.ps1
```

Nếu Windows chặn script do execution policy, chạy một lần:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-microservices.ps1
```

Script tự sinh token nội bộ dùng chung, mở Auth, POI, Presence và Gateway trong bốn cửa sổ. Mở `http://localhost:8000/login.html`; dừng từng service bằng `Ctrl+C` trong cửa sổ tương ứng. Không chạy backend nguyên khối cũ cùng lúc vì Gateway cũng cần cổng `8000`.

Để chạy bằng Docker Compose trên máy phát triển:

1. Cài Docker Desktop và bật TCP/IP cho SQL Server. Container Linux không dùng được Windows Integrated Authentication; cần `DATABASE_URL` dùng SQL login tới SQL Server mà máy Docker truy cập được.
2. Sao chép `.env.microservices.example` thành `.env.microservices`; thay `DATABASE_URL`, `JWT_SECRET`, `INTERNAL_SERVICE_TOKEN` và mật khẩu admin bằng giá trị riêng. Tạo hai secret ngẫu nhiên riêng cho `JWT_SECRET` và `INTERNAL_SERVICE_TOKEN` (có thể chạy `python -c "import secrets; print(secrets.token_urlsafe(48))"` hai lần); giữ cùng một `INTERNAL_SERVICE_TOKEN` cho các service và gateway. Không commit file `.env.microservices`.
3. Chạy từ thư mục gốc:

   ```powershell
   docker compose --env-file .env.microservices -f compose.microservices.yaml up --build
   ```

4. Mở `http://localhost:8000`. Dừng các service bằng `Ctrl+C`; xóa container bằng `docker compose --env-file .env.microservices -f compose.microservices.yaml down`. Volume `poi-uploads` được giữ lại.

Auth service khởi tạo schema SQL Server; POI, Presence và Gateway chờ schema sẵn sàng rồi mới phục vụ request. Các tiến trình dùng chung SQL Server `CNPM` và Redis; không tạo thêm database. API báo cáo được Gateway phục vụ trực tiếp từ bảng Visit hiện có. Các file audio thuộc POI được lưu trong volume riêng của POI service.

Nếu đang dùng SQL Server Express/Redis cài trực tiếp trên Windows và chưa có Docker, có thể chạy bốn tiến trình bằng bốn cửa sổ PowerShell thay vì Compose. Tạo một `INTERNAL_SERVICE_TOKEN` bằng lệnh dưới đây rồi dùng **cùng một giá trị** trong cả bốn cửa sổ:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Trong mỗi cửa sổ, chạy `Set-Location .\backend-api`, đặt `INTERNAL_SERVICE_TOKEN` thành token vừa tạo và đặt `SERVICE_ROLE` lần lượt là `auth`, `poi`, `presence` hoặc `gateway`. Khởi động từng tiến trình bằng lệnh sau, thay giá trị port:

```powershell
$env:INTERNAL_SERVICE_TOKEN = "DAN_TOKEN_VAO_DAY"
$env:SERVICE_ROLE = "auth"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8101
```

Dùng port `8101` cho Auth, `8102` cho POI, `8103` cho Presence và `8000` cho Gateway. Khởi động Auth trước để tạo schema, rồi POI và Presence; khởi động Gateway sau cùng. Trong cửa sổ Gateway, đặt thêm:

```powershell
$env:AUTH_SERVICE_URL = "http://127.0.0.1:8101"
$env:POI_SERVICE_URL = "http://127.0.0.1:8102"
$env:PRESENCE_SERVICE_URL = "http://127.0.0.1:8103"
$env:PUBLIC_BASE_URL = "http://localhost:8000"
$env:PUBLIC_APP_URL = "http://localhost:8000"
```

Đảm bảo `.env` đang dùng `DEMO_MODE=false`, `DATABASE_URL` trỏ tới SQL Server `CNPM` và Redis đang chạy. Khi dừng, đóng cả bốn cửa sổ; lệnh Uvicorn nguyên khối cũ vẫn chạy như trước nếu không đặt `SERVICE_ROLE`.

### CD lên Render

`render.yaml` vẫn mô tả triển khai một backend nguyên khối để giữ cách triển khai cũ. Để triển khai bốn service riêng, dùng Blueprint `render-microservices.yaml`:

1. Tạo SQL Server và Redis có thể truy cập từ Render. Cấu hình trong firewall quyền truy cập cần thiết; không dùng `localhost` và không mở SQL Server công khai nếu nhà cung cấp có private networking.
2. Trong Render chọn **New > Blueprint**, kết nối repository và chọn `render-microservices.yaml`. Điền `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `INTERNAL_SERVICE_TOKEN`, `ADMIN_SEED_EMAIL` và `ADMIN_SEED_PASSWORD` cho các service. Các service phải dùng **cùng** database, Redis, JWT secret và internal token. Giữ các giá trị bí mật trong Environment của Render, không commit vào repository.
3. Gateway lấy host của Auth, POI và Presence service từ Blueprint; người dùng chỉ truy cập URL gateway. Endpoint nghiệp vụ của các service nội bộ yêu cầu token; health check `/api/health` được phép truy cập để Render kiểm tra.
4. Chạy `python -m app.seed_admin` một lần trong môi trường có cùng `DATABASE_URL` và cấu hình admin production.
5. Để bật CD cho bốn service, thêm GitHub Actions secrets `RENDER_GATEWAY_DEPLOY_HOOK`, `RENDER_AUTH_DEPLOY_HOOK`, `RENDER_POI_DEPLOY_HOOK` và `RENDER_PRESENCE_DEPLOY_HOOK`, mỗi secret lấy từ đúng service Render. Push lên nhánh mặc định sẽ deploy cả bốn service **chỉ sau khi CI thành công**. Phải cấu hình đủ cả bốn hook; nếu không, workflow sẽ báo lỗi thay vì deploy một phần. Secret `RENDER_DEPLOY_HOOK` cũ vẫn dùng được với Blueprint nguyên khối.

Các service trên gói Free có thể ngủ khi không có truy cập và cần thời gian khởi động lại. Filesystem Render là tạm thời; cần persistent storage hoặc object storage nếu muốn lưu audio production bền vững qua deploy/restart.

Dữ liệu cần thiết từ MongoDB cũ đã được chuyển vào database SQL Server `CNPM`; database MongoDB nguồn được giữ nguyên để dự phòng. Service Render dùng filesystem tạm cho MP3, nên file có thể mất khi restart/deploy; cần cấu hình lưu trữ bền vững nếu muốn giữ audio production.

## Checklist kiểm thử thực tế trước khi trình bày

Các test tự động không thay thế việc kiểm thử SQL Server/Redis thật, GPS trên điện thoại hoặc thiết bị phát audio. Chạy thử từng bước và điền kết quả/ngày kiểm tra; không đánh dấu hoàn thành nếu chưa thực hiện.

| # | Kịch bản | Kết quả mong đợi | Kết quả thực tế |
|---|---|---|---|
| 1 | Khởi động SQL Server, Redis và backend; mở `/api/health` | Health trả về trạng thái `ok`; backend không báo lỗi kết nối | Chưa kiểm tra |
| 2 | Đăng nhập admin bằng tài khoản đã seed | Đăng nhập thành công; trang quản trị hiện theo đúng vai trò | Chưa kiểm tra |
| 3 | Tạo POI có tọa độ và bán kính geofence | POI được lưu và xuất hiện trên bản đồ/danh sách khách | Chưa kiểm tra |
| 4 | Thêm nội dung tiếng Việt, tạo hoặc nhập bản dịch, audio; duyệt bản dịch | Nội dung đã xuất bản và audio đúng ngôn ngữ được trả cho khách | Chưa kiểm tra |
| 5 | Mở trang khách trên máy tính, chọn ngôn ngữ và phát audio từ danh sách | Chi tiết POI hiển thị; audio phát hoặc có thông báo rõ nếu thiếu audio | Chưa kiểm tra |
| 6 | Mở link `/access-qr` trên máy tính, quét QR bằng điện thoại qua HTTPS và cho phép vị trí | Trang khách mở được; trạng thái GPS cập nhật; vị trí được xác định | Chưa kiểm tra |
| 7 | Đi vào vùng geofence POI đã cấu hình | POI gần nhất được nhận biết; audio tự phát hoặc hiện nút phát thủ công | Chưa kiểm tra |
| 8 | Mở trang giám sát admin khi khách đang kết nối | Số khách trực tuyến cập nhật; khách rời đi sẽ hết hạn khỏi trạng thái online | Chưa kiểm tra |
| 9 | Tạo dữ liệu lượt tham quan rồi mở báo cáo và xuất CSV/XLSX/PDF | Báo cáo phản ánh dữ liệu đã tạo; tệp xuất mở được | Chưa kiểm tra |
| 10 | Thử đăng nhập với vai trò/quyền hạn khác nhau và truy cập thao tác bị cấm | Hành động bị chặn ở API với phản hồi 401/403 phù hợp | Chưa kiểm tra |

Ngày kiểm thử: __________  Thiết bị/trình duyệt: __________  Người kiểm thử: __________

## Tiêu chí hoàn thành

| Mục | Nội dung                                                                 | Trạng thái |
| --- | ------------------------------------------------------------------------ | ---------- |
| A1  | FastAPI, SQL Server/Redis, `.env`, health, CORS                           | Hoàn thành |
| A2  | Login/logout/me với JWT cookie HttpOnly                                  | Hoàn thành |
| A3  | Bốn vai trò và kiểm tra 403                                              | Hoàn thành |
| A4  | POI công khai, tìm gần, CRUD, bản dịch và geofence                       | Hoàn thành |
| A5  | Edge TTS và MP3 upload tối đa 20 MiB                                     | Hoàn thành |
| A6  | Dịch Gemini, sửa, duyệt và fallback nội dung                             | Hoàn thành |
| A8  | WebSocket khách/admin, online, số theo POI và cảnh báo >50               | Hoàn thành |
| A9  | Lưu vị trí và API heatmap                                                | Hoàn thành |
| A11 | CRUD tài khoản admin có bảo vệ thao tác tự thân                          | Hoàn thành |
| A12 | Báo cáo POI/ngôn ngữ/ngày và CSV/XLSX/PDF                                | Hoàn thành |
| A13 | Log kết nối, vào POI, rời POI                                            | Hoàn thành |
| A14 | Pytest theo từng nhóm A1-A13 với SQLite/fakeredis                         | Hoàn thành |
| B1  | Login, kiểm tra phiên, logout                                            | Hoàn thành |
| B2  | Khung dashboard và menu theo quyền                                       | Hoàn thành |
| B3  | Tổng quan online, POI và realtime                                        | Hoàn thành |
| B4  | Bảng POI phân trang, CRUD và chọn vị trí trên bản đồ OpenStreetMap        | Hoàn thành |
| B5  | Sinh audio và tải MP3 trong form POI                                     | Hoàn thành |
| B6  | Trạng thái, dịch, sửa và duyệt bản dịch                                  | Hoàn thành |
| B8  | WebSocket tự kết nối lại, khách theo POI và heatmap                      | Hoàn thành |
| B9  | Gửi cảnh báo có xác nhận mật khẩu và lịch sử                             | Hoàn thành |
| B10 | Biểu đồ POI/ngày và xuất XLSX/PDF/CSV                                    | Hoàn thành |
| B11 | Quản lý tài khoản, chỉ super admin thấy                                  | Hoàn thành |

## Giả định

- Mặc định cả dashboard, trang khách và API được phục vụ từ `localhost:8000`. Cổng `5500` chỉ dùng nếu cần phục vụ frontend riêng; API vẫn ở `8000`.
- API hiện chưa có thao tác kết thúc cảnh báo hoặc thời hạn do admin cấu hình; dashboard tạm xem cảnh báo tạo trong 24 giờ gần nhất là còn hiệu lực. Lịch sử cảnh báo vẫn được giữ và hiển thị riêng.
- Mỗi kết nối WebSocket là một khách; khách được tính theo POI khi heartbeat gửi `poi_id`. Heartbeat khuyến nghị mỗi 15 giây; presence hết hạn sau 45 giây. Tọa độ chỉ được lưu khi khách gửi tọa độ.
- Bản dịch nội dung tạo trực tiếp trong POI được xem là đã xuất bản; bản dịch Gemini là bản nháp cho tới khi duyệt. Khách nhận nội dung đã xuất bản theo thứ tự ngôn ngữ yêu cầu, tiếng Anh, tiếng Việt.
- Ảnh POI dùng URL; upload file chỉ dành cho MP3. Ứng dụng khách và admin được phục vụ chung từ thư mục `admin-dashboard`.
- Trong trang Điểm tham quan của dashboard, dùng nút “Thêm khu tham quan” để tạo điểm độc lập; dùng “Thêm hiện vật” để tạo hiện vật và bắt buộc chọn khu tham quan cha. Mỗi hiện vật có tọa độ geofence và audio riêng; hệ thống hỗ trợ một cấp cha-con. Trang tour theo dõi geofence từng POI mục tiêu, gửi POI hiện tại trong heartbeat, ghi sự kiện vào/rời POI và tự phát audio xuất bản tương ứng. Khi trình duyệt chặn autoplay sẽ hiện nút phát thủ công. GPS trên trình duyệt di động ngoài localhost yêu cầu HTTPS.
- Báo cáo tính lượt theo sự kiện `poi_enter`, ngày theo UTC và tính trọn ngày kết thúc. PDF dùng mã POI; CSV/Excel chứa tên POI.
- Bộ test không xác nhận kết nối SQL Server, Redis, Gemini hoặc Edge TTS thật.
