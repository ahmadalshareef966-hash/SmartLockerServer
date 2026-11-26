import os
import time
import random
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# قاعدة بيانات مؤقتة لإدارة الصندوقين بالوقت الفعلي
boxes_db = {
    "box_1": {"otp": None, "expires_at": 0, "phone": None, "unlock_seconds": 5},
    "box_2": {"otp": None, "expires_at": 0, "phone": None, "unlock_seconds": 5},
}

# قراءة المفاتيح السرية من Environment Variables في Render
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
ESP_API_KEY = os.environ.get("ESP_API_KEY", "")


def send_whatsapp_message(phone, box_name, otp, duration_label):
    if not WHATSAPP_API_URL or not WHATSAPP_TOKEN or not phone:
        print(f"[Whatsapp Simulation] To: {phone} | Box: {box_name} | OTP: {otp} | Duration: {duration_label}")
        return False

    message = (
        "أهلاً بك في نظام الصناديق الذكية\n"
        "تم تأكيد حجزك بنجاح!\n"
        f"الصندوق: {box_name}\n"
        f"رمز الدخول (OTP): {otp}\n"
        f"المدة: {duration_label}"
    )

    try:
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "phone": phone,
            "message": message,
        }
        resp = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"[Whatsapp Error] {e}")
        return False


def normalize_box_id(raw_box):
    if not raw_box:
        return None
    cleaned = str(raw_box).strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "box_1": "box_1",
        "box1": "box_1",
        "1": "box_1",
        "box_2": "box_2",
        "box2": "box_2",
        "2": "box_2",
    }
    return mapping.get(cleaned)


def compute_unlock_seconds(data):
    for key in ["duration_sec", "unlock_duration", "duration", "seconds"]:
        if key in data and data[key] is not None:
            try:
                val = int(float(data[key]))
                if val > 0:
                    return max(2, min(60, val))
            except (ValueError, TypeError):
                pass

    if "duration_min" in data and data["duration_min"] is not None:
        try:
            mins = float(data["duration_min"])
            if mins > 0:
                return max(2, min(60, int(mins * 60)))
        except (ValueError, TypeError):
            pass

    if "hours" in data and data["hours"] is not None:
        try:
            hrs = float(data["hours"])
            if hrs > 0:
                return max(5, min(60, int(hrs * 10)))
        except (ValueError, TypeError):
            pass

    return 5


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>نظام الصندوق الذكي لتسليم الطرود</title>
  <style>
    * { box-sizing: border-box; font-family: Tahoma, Arial, sans-serif; }
    body {
      margin: 0;
      min-height: 100vh;
      background: linear-gradient(135deg, #0f172a, #1e293b);
      color: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .card {
      width: 100%;
      max-width: 460px;
      background: #111827;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 20px 45px rgba(0,0,0,0.45);
    }
    h1 { margin: 0 0 8px; font-size: 22px; text-align: center; color: #38bdf8; }
    p.sub { margin: 0 0 20px; font-size: 13px; text-align: center; color: #94a3b8; }
    label { display: block; margin-bottom: 6px; font-size: 14px; color: #cbd5e1; }
    select, input {
      width: 100%;
      padding: 12px;
      margin-bottom: 16px;
      border-radius: 10px;
      border: 1px solid #334155;
      background: #1e293b;
      color: #fff;
      font-size: 15px;
    }
    button {
      width: 100%;
      padding: 14px;
      border: none;
      border-radius: 10px;
      background: #0ea5e9;
      color: #fff;
      font-size: 16px;
      font-weight: bold;
      cursor: pointer;
    }
    button:hover { background: #0284c7; }
    .result {
      margin-top: 20px;
      padding: 16px;
      border-radius: 12px;
      background: #0f172a;
      border: 1px solid #22c55e;
      text-align: center;
      display: none;
    }
    .otp-code {
      font-size: 36px;
      font-weight: bold;
      letter-spacing: 6px;
      color: #4ade80;
      margin: 10px 0;
    }
    .status-bar {
      margin-top: 18px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .box-pill {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 10px;
      font-size: 12px;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>الصندوق الذكي لتسليم الطرود</h1>
    <p class="sub">توليد رمز فتح القفل (OTP) وربطه مباشرة بالصندوق</p>

    <label for="boxSelect">اختر الصندوق</label>
    <select id="boxSelect">
      <option value="box_1">البوكس الأول (box_1)</option>
      <option value="box_2">البوكس الثاني (box_2)</option>
    </select>

    <label for="durationSelect">مدة فتح القفل (بالثواني)</label>
    <select id="durationSelect">
      <option value="5">5 ثوانٍ</option>
      <option value="10" selected>10 ثوانٍ</option>
      <option value="15">15 ثانية</option>
      <option value="20">20 ثانية</option>
      <option value="30">30 ثانية</option>
    </select>

    <label for="phoneInput">رقم الجوال (اختياري للواتساب)</label>
    <input id="phoneInput" type="text" placeholder="9665XXXXXXXX" />

    <button onclick="generateCode()">توليد الكود الآن</button>

    <div id="resultBox" class="result">
      <div id="resultTitle" style="color:#94a3b8;font-size:13px;"></div>
      <div id="otpDisplay" class="otp-code">----</div>
      <div id="resultHint" style="color:#e2e8f0;font-size:13px;"></div>
    </div>

    <div class="status-bar" id="statusBar"></div>
  </div>

  <script>
    async function refreshStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        const bar = document.getElementById('statusBar');
        bar.innerHTML = '';
        for (const [box, info] of Object.entries(data.boxes)) {
          const active = info.has_otp ? `كود نشط (${info.unlock_seconds}ث)` : 'جاهز / فارغ';
          bar.innerHTML += `<div class="box-pill"><strong>${box}</strong><br>${active}</div>`;
        }
      } catch (e) {}
    }

    async function generateCode() {
      const box_id = document.getElementById('boxSelect').value;
      const duration_sec = Number(document.getElementById('durationSelect').value);
      const phone = document.getElementById('phoneInput').value.trim();

      const res = await fetch('/api/generate-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          box_id,
          duration_sec,
          duration_label: `${duration_sec} ثانية`,
          phone: phone || null
        })
      });

      const data = await res.json();
      const resultBox = document.getElementById('resultBox');
      if (data.success) {
        resultBox.style.display = 'block';
        document.getElementById('resultTitle').innerText = `تم تفعيل الكود على ${data.box_id}`;
        document.getElementById('otpDisplay').innerText = data.otp;
        document.getElementById('resultHint').innerText =
          `أدخل الكود ${data.otp}# على لوحة المفاتيح ليفتح القفل لمدة ${data.duration_sec} ثوانٍ`;
        refreshStatus();
      } else {
        alert(data.message || 'حدث خطأ');
      }
    }

    refreshStatus();
    setInterval(refreshStatus, 5000);
  </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML_PAGE)


@app.route("/api/status", methods=["GET"])
def status():
    now = time.time()
    summary = {}
    for box_id, info in boxes_db.items():
        valid = bool(info.get("otp")) and now <= info.get("expires_at", 0)
        summary[box_id] = {
            "has_otp": valid,
            "unlock_seconds": info.get("unlock_seconds", 5),
        }
    return jsonify({"status": "online", "boxes": summary}), 200


@app.route("/api/generate-otp", methods=["POST"])
def generate_otp():
    data = request.get_json(silent=True) or {}
    box_id = normalize_box_id(data.get("box_id") or data.get("boxId") or data.get("box"))
    if not box_id or box_id not in boxes_db:
        return jsonify({"success": False, "valid": False, "message": "Unknown Box"}), 400

    phone = data.get("phone")
    otp = str(data.get("otp") or random.randint(1000, 9999)).strip()
    unlock_seconds = compute_unlock_seconds(data)
    duration_label = data.get("duration_label") or f"{unlock_seconds}s"

    ttl_seconds = int(data.get("ttl_seconds", 600))
    boxes_db[box_id] = {
        "otp": otp,
        "expires_at": time.time() + ttl_seconds,
        "phone": phone,
        "unlock_seconds": unlock_seconds,
    }

    if phone:
        send_whatsapp_message(phone, box_id, otp, duration_label)

    return jsonify({
        "success": True,
        "valid": True,
        "box_id": box_id,
        "otp": otp,
        "duration_sec": unlock_seconds,
        "unlock_duration": unlock_seconds,
        "message": f"OTP generated for {box_id}"
    }), 200


@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json(silent=True) or {}

    incoming_key = (
        request.headers.get("X-API-Key")
        or request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        or data.get("api_key")
    )
    if ESP_API_KEY and incoming_key and incoming_key != ESP_API_KEY:
        return jsonify({"success": False, "valid": False, "message": "Unauthorized"}), 401

    raw_box = data.get("box_id") or data.get("boxId") or data.get("box")
    box_id = normalize_box_id(raw_box)
    otp = str(data.get("otp") or data.get("code") or "").strip()

    if not box_id or box_id not in boxes_db:
        return jsonify({"success": False, "valid": False, "message": "Unknown Box"}), 400

    if not otp:
        return jsonify({"success": False, "valid": False, "message": "OTP required"}), 400

    record = boxes_db[box_id]
    if not record.get("otp") or record["otp"] != otp:
        return jsonify({"success": False, "valid": False, "message": "Invalid OTP"}), 401

    if time.time() > record.get("expires_at", 0):
        boxes_db[box_id]["otp"] = None
        return jsonify({"success": False, "valid": False, "message": "OTP Expired"}), 401

    unlock_seconds = int(record.get("unlock_seconds", 5))
    boxes_db[box_id]["otp"] = None
    boxes_db[box_id]["expires_at"] = 0

    return jsonify({
        "success": True,
        "valid": True,
        "box_id": box_id,
        "duration_sec": unlock_seconds,
        "unlock_duration": unlock_seconds,
        "message": "Access Granted"
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
