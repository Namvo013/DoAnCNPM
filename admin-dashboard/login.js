const API_ORIGIN = new URL(window.location.origin);
if (API_ORIGIN.port === "5500") API_ORIGIN.port = "8000";
const API_ROOT = `${API_ORIGIN.origin}/api`;

const loginForm = document.querySelector("#login-form");
const loginError = document.querySelector("#login-error");

async function readError(response) {
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  const detail = payload.detail;
  if (typeof detail === "string" && /[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i.test(detail)) {
    return detail;
  }
  if (response.status === 401) return "Email hoặc mật khẩu không chính xác.";
  if (response.status === 403) return "Tài khoản đã bị khóa hoặc không có quyền truy cập.";
  if (response.status >= 500) return "Máy chủ đang gặp sự cố. Vui lòng thử lại sau.";
  return "Không thể đăng nhập. Vui lòng kiểm tra thông tin và thử lại.";
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = loginForm.querySelector("button[type=submit]");
  const formData = new FormData(loginForm);
  submit.disabled = true;
  submit.textContent = "Đang xác thực...";
  loginError.hidden = true;
  try {
    const response = await fetch(`${API_ROOT}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: formData.get("email"),
        password: formData.get("password"),
      }),
    });
    if (!response.ok) throw new Error(await readError(response));
    window.location.replace("index.html");
  } catch (error) {
    loginError.textContent = error.message || "Không thể kết nối máy chủ. Hãy kiểm tra backend.";
    loginError.hidden = false;
  } finally {
    submit.disabled = false;
    submit.textContent = "Đăng nhập";
  }
});

fetch(`${API_ROOT}/auth/me`, { credentials: "include" })
  .then((response) => {
    if (response.ok) window.location.replace("index.html");
  })
  .catch(() => {});
