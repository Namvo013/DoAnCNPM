import io
import socket
from html import escape

import qrcode
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from qrcode.image.svg import SvgPathImage

router = APIRouter(tags=["mobile access"])


def get_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(("8.8.8.8", 80))
            address = connection.getsockname()[0]
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to detect this computer's local network address",
        ) from error
    if address.startswith("127."):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No local network address is available",
        )
    return address


@router.get("/access-qr", response_class=HTMLResponse, include_in_schema=False)
async def mobile_access_qr(request: Request) -> HTMLResponse:
    if request.url.hostname in {"localhost", "127.0.0.1", "::1"}:
        authority = f"{get_lan_ip()}:{request.url.port or 8000}"
    else:
        authority = request.url.netloc
    target_url = f"{request.url.scheme}://{authority}/tourist-pwa/tour.html"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(target_url)
    qr.make(fit=True)
    image = qr.make_image(image_factory=SvgPathImage)
    output = io.BytesIO()
    image.save(output)
    svg = output.getvalue().decode("utf-8")
    page = f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mã QR truy cập ứng dụng khách</title>
  <style>
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px; box-sizing: border-box; background: #f3f6fb; color: #182230; font: 16px "Segoe UI", sans-serif; text-align: center; }}
    main {{ width: min(440px, 100%); padding: 28px; box-sizing: border-box; border: 1px solid #e1e7ef; border-radius: 20px; background: #fff; box-shadow: 0 12px 36px #24334d18; }}
    .qr {{ width: min(320px, 85vw); height: auto; padding: 12px; border: 1px solid #e1e7ef; border-radius: 12px; background: #fff; }}
    a {{ color: #075ac8; overflow-wrap: anywhere; }}
    p {{ line-height: 1.6; color: #445166; }}
  </style>
</head>
<body>
  <main>
    <h1>Mã QR truy cập ứng dụng khách</h1>
    <p>Để điện thoại và máy tính cùng kết nối một mạng Wi-Fi, sau đó quét mã này.</p>
    <div class="qr">{svg}</div>
    <p><a href="{escape(target_url, quote=True)}">{escape(target_url)}</a></p>
    <p>Nếu điện thoại không kết nối được, hãy cho phép Python/Uvicorn qua Windows Firewall trên mạng riêng.</p>
  </main>
</body>
</html>"""
    return HTMLResponse(page, headers={"Cache-Control": "no-store"})
