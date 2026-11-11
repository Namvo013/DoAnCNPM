# Hệ thống Thuyết minh Du lịch Đa ngôn ngữ

Backend FastAPI và trang Admin Dashboard HTML/CSS/JavaScript thuần. REST API dùng prefix `/api`, tài liệu tại `http://localhost:8000/docs`.

## Chạy backend trên Windows

Yêu cầu Python 3.10+, MongoDB và Redis đang chạy. Mở PowerShell tại thư mục dự án:

```powershell
Set-Location .\backend-api
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env
```

Dán secret vừa tạo vào `JWT_SECRET` trong `.env`, đặt `ADMIN_SEED_PASSWORD` dài ít nhất 12 ký tự, và kiểm tra URL MongoDB/Redis. Cài dependency, tạo super admin ban đầu và chạy API:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m app.seed_admin
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API chạy ở `http://localhost:8000`. Kiểm tra `http://localhost:8000/api/health` hoặc mở Swagger `/docs`. Có thể đặt `GEMINI_API_KEY` để bật dịch Gemini. `COOKIE_SECURE=true` chỉ dùng khi triển khai HTTPS.

### Chạy thử không cần MongoDB/Redis

Để xem thử đăng nhập/dashboard trên máy cá nhân mà chưa cài MongoDB và Redis, cài dependencies dev rồi đặt `ENVIRONMENT=development`, `DEMO_MODE=true`, `ADMIN_SEED_EMAIL` thành email thử nghiệm và `ADMIN_SEED_PASSWORD` thành mật khẩu riêng dài ít nhất 12 ký tự trong `.env`. Khởi động API như trên; chế độ demo tự tạo tài khoản khi chạy và dùng cơ sở dữ liệu/cache trong bộ nhớ, nên dữ liệu mất khi dừng server. Chỉ dùng cho máy local; không bật `DEMO_MODE` trong môi trường triển khai.

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

Test sử dụng `mongomock-motor` và `fakeredis`, không cần MongoDB/Redis đang chạy. Gemini và Edge TTS được kiểm thử qua mock/fake, không gọi dịch vụ thật.

### CI tự động

GitHub Actions tự cài backend cùng dependencies kiểm thử và chạy toàn bộ pytest khi có push, pull request hoặc chạy thủ công từ tab **Actions**. Workflow ở `.github/workflows/backend-ci.yml`.

### CD lên Render

Blueprint `render.yaml` tạo web service chạy API cùng Admin Dashboard và trang khách. Để bật triển khai tự động:

1. Tạo MongoDB có thể truy cập từ Render (ví dụ MongoDB Atlas) và Redis có TLS; không dùng địa chỉ `localhost` cho dịch vụ triển khai.
2. Trong Render, chọn **New > Blueprint**, kết nối repository GitHub này và áp dụng `render.yaml`. Điền `MONGODB_URL`, `REDIS_URL`, `ADMIN_SEED_EMAIL` và `ADMIN_SEED_PASSWORD` (ít nhất 12 ký tự). Blueprint tự sinh `JWT_SECRET`; không đưa secret vào repository.
3. Trong GitHub repository, thêm Actions secret `RENDER_DEPLOY_HOOK` với deploy hook URL lấy trong phần Settings của web service Render.
4. Sau khi service được tạo, đặt `PUBLIC_BASE_URL` và `PUBLIC_APP_URL` trong Environment của Render thành URL HTTPS công khai của service rồi lưu thay đổi.
5. Tạo super admin một lần bằng cách chạy `python -m app.seed_admin` tại thư mục `backend-api`, với các biến môi trường production được cấu hình trong `.env` trỏ tới MongoDB đã deploy. Không chạy lại sau khi đã có tài khoản admin.

Sau khi cấu hình secret, push lên nhánh mặc định sẽ deploy Render **chỉ khi job test CI thành công**. Nếu chưa thêm secret thì job deploy sẽ bỏ qua; pull request và các nhánh khác không deploy. Health check dùng `/api/health`.

Service mặc định dùng gói Free và lưu file MP3 trong filesystem tạm của instance; các file upload có thể mất khi service khởi động lại hoặc deploy. Dữ liệu chính phải lưu trong MongoDB/Redis bên ngoài; nếu cần giữ file MP3 ổn định, cần cấu hình lưu trữ bền vững riêng trước khi sử dụng production.

## Checklist kiểm thử thực tế trước khi trình bày

Các test tự động không thay thế việc kiểm thử MongoDB/Redis thật, GPS trên điện thoại hoặc thiết bị phát audio. Chạy thử từng bước và điền kết quả/ngày kiểm tra; không đánh dấu hoàn thành nếu chưa thực hiện.

| # | Kịch bản | Kết quả mong đợi | Kết quả thực tế |
|---|---|---|---|
| 1 | Khởi động MongoDB, Redis và backend; mở `/api/health` | Health trả về trạng thái `ok`; backend không báo lỗi kết nối | Chưa kiểm tra |
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
| A1  | FastAPI, MongoDB/Redis, `.env`, health, CORS                             | Hoàn thành |
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
| A14 | Pytest theo từng nhóm A1-A13 với fakeredis/mongomock-motor               | Hoàn thành |
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
- Bộ test không xác nhận kết nối MongoDB, Redis, Gemini hoặc Edge TTS thật.
