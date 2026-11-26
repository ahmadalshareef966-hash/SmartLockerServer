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
    :root {
      --bg: #070d19;
      --card: #0f172a;
      --card-2: #162036;
      --border: #263554;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #0ea5e9;
      --accent-hover: #0284c7;
      --success: #22c55e;
      --danger: #ef4444;
      --warn: #f59e0b;
    }
    * { box-sizing: border-box; font-family: Tahoma, Arial, sans-serif; transition: all 0.2s ease; }
    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(circle at top, #132242 0%, var(--bg) 70%);
      color: var(--text);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .shell {
      width: 100%;
      max-width: 540px;
      background: rgba(15, 23, 42, 0.94);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.55);
      backdrop-filter: blur(10px);
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 18px;
    }
    h1 { margin: 0; font-size: 21px; color: #38bdf8; }
    .sub { margin: 4px 0 0; font-size: 12.5px; color: var(--muted); }
    .live-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(34, 197, 94, 0.12);
      border: 1px solid rgba(34, 197, 94, 0.35);
      color: #4ade80;
      font-size: 12px;
      white-space: nowrap;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #4ade80;
      box-shadow: 0 0 10px #4ade80;
      animation: pulse 1.6s infinite;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.35); opacity: 0.65; }
    }

    .section-title {
      font-size: 13px;
      color: #cbd5e1;
      margin: 14px 0 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .box-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .box-card {
      background: var(--card-2);
      border: 1.5px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      cursor: pointer;
      text-align: right;
      position: relative;
    }
    .box-card:hover { border-color: #38bdf8; transform: translateY(-2px); }
    .box-card.active {
      border-color: #38bdf8;
      background: linear-gradient(145deg, rgba(14, 165, 233, 0.16), var(--card-2));
      box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.35);
    }
    .box-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .box-name { font-weight: bold; font-size: 15px; color: #fff; }
    .pill {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(148, 163, 184, 0.15);
      color: #cbd5e1;
    }
    .pill.active-otp {
      background: rgba(34, 197, 94, 0.18);
      color: #4ade80;
      border: 1px solid rgba(34, 197, 94, 0.35);
    }
    .box-meta { font-size: 12px; color: var(--muted); }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }
    .chip {
      padding: 8px 13px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--card-2);
      color: #e2e8f0;
      font-size: 13px;
      cursor: pointer;
    }
    .chip.selected {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      font-weight: bold;
    }
    .custom-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
    }
    input[type="range"] { flex: 1; accent-color: var(--accent); cursor: pointer; }
    .sec-box {
      min-width: 72px;
      text-align: center;
      padding: 7px 10px;
      border-radius: 10px;
      background: var(--card-2);
      border: 1px solid var(--border);
      font-size: 13px;
      font-weight: bold;
      color: #38bdf8;
    }

    input[type="text"] {
      width: 100%;
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: var(--card-2);
      color: #fff;
      font-size: 14px;
      margin-bottom: 14px;
    }
    input[type="text"]:focus { outline: none; border-color: var(--accent); }

    .btn-primary {
      width: 100%;
      padding: 14px;
      border: none;
      border-radius: 12px;
      background: linear-gradient(90deg, #0284c7, #0ea5e9);
      color: #fff;
      font-size: 15px;
      font-weight: bold;
      cursor: pointer;
      box-shadow: 0 10px 24px rgba(14, 165, 233, 0.28);
    }
    .btn-primary:hover { filter: brightness(1.08); transform: translateY(-1px); }

    .result-card {
      margin-top: 18px;
      padding: 18px;
      border-radius: 16px;
      background: rgba(20, 83, 45, 0.22);
      border: 1px solid rgba(74, 222, 128, 0.45);
      display: none;
    }
    .result-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12.5px;
      color: #bbf7d0;
    }
    .otp-big {
      font-size: 40px;
      font-weight: bold;
      letter-spacing: 8px;
      color: #4ade80;
      text-align: center;
      margin: 10px 0;
      direction: ltr;
    }
    .keypad-sim {
      background: #090f1d;
      border: 1px solid #1e293b;
      border-radius: 10px;
      padding: 10px;
      text-align: center;
      font-size: 13px;
      color: #e2e8f0;
      margin-bottom: 12px;
    }
    .keypad-sim code {
      color: #38bdf8;
      font-size: 15px;
      font-weight: bold;
    }
    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .btn-secondary {
      padding: 10px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--card-2);
      color: #f1f5f9;
      font-size: 13px;
      cursor: pointer;
    }
    .btn-secondary:hover { border-color: #38bdf8; }
    .btn-danger {
      padding: 10px;
      border-radius: 10px;
      border: 1px solid rgba(239, 68, 68, 0.4);
      background: rgba(239, 68, 68, 0.14);
      color: #fca5a5;
      font-size: 13px;
      cursor: pointer;
    }
    .toast {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%) translateY(20px);
      background: #0f172a;
      color: #fff;
      border: 1px solid #38bdf8;
      padding: 10px 18px;
      border-radius: 999px;
      font-size: 13px;
      opacity: 0;
      pointer-events: none;
      z-index: 50;
    }
    .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
  </style>
</head>
<body>
  <div class="shell">
    <div class="header">
      <div>
        <h1>الصندوق الذكي لتسليم الطرود</h1>
        <p class="sub">تحكم تفاعلي بالصندوقين والمدة الزمنية ورمز التحقق (OTP)</p>
      </div>
      <div class="live-badge"><span class="dot"></span> متصل بالسيرفر</div>
    </div>

    <div class="section-title">
      <span>1. اختر الصندوق المستهدف</span>
      <span id="selectedBoxLabel" style="color:#38bdf8;font-weight:bold;">box_1</span>
    </div>
    <div class="box-grid">
      <div class="box-card active" id="card_box_1" onclick="selectBox('box_1')">
        <div class="box-top">
          <span class="box-name">البوكس الأول</span>
          <span class="pill" id="pill_box_1">فارغ</span>
        </div>
        <div class="box-meta" id="meta_box_1">المعرف: box_1 • جاهز</div>
      </div>

      <div class="box-card" id="card_box_2" onclick="selectBox('box_2')">
        <div class="box-top">
          <span class="box-name">البوكس الثاني</span>
          <span class="pill" id="pill_box_2">فارغ</span>
        </div>
        <div class="box-meta" id="meta_box_2">المعرف: box_2 • جاهز</div>
      </div>
    </div>

    <div class="section-title">
      <span>2. مدة بقاء القفل مفتوحاً (بالثواني)</span>
      <span id="durationHint" style="color:#94a3b8;font-size:12px;">يُرسل للـ ESP32 كـ duration_sec</span>
    </div>
    <div class="chips" id="presetChips">
      <button type="button" class="chip" onclick="setDuration(5)">5 ث</button>
      <button type="button" class="chip selected" onclick="setDuration(10)">10 ث</button>
      <button type="button" class="chip" onclick="setDuration(15)">15 ث</button>
      <button type="button" class="chip" onclick="setDuration(20)">20 ث</button>
      <button type="button" class="chip" onclick="setDuration(30)">30 ث</button>
    </div>
    <div class="custom-row">
      <input type="range" id="durationSlider" min="2" max="60" value="10" oninput="setDuration(this.value)" />
      <div class="sec-box" id="durationBadge">10 ث</div>
    </div>

    <div class="section-title">
      <span>3. رقم الجوال (اختياري لإرسال واتساب)</span>
    </div>
    <input type="text" id="phoneInput" placeholder="9665XXXXXXXX" />

    <button type="button" class="btn-primary" id="genBtn" onclick="generateCode()">
      توليد وتفعيل كود OTP الآن
    </button>

    <div class="result-card" id="resultCard">
      <div class="result-top">
        <span id="resBoxInfo">الصندوق: box_1</span>
        <span id="resTimer">صالح لمدة: --:--</span>
      </div>
      <div class="otp-big" id="otpValue">----</div>
      <div class="keypad-sim">
        على لوحة مفاتيح الصندوق اكتب: <code id="keypadSeq">----#</code>
        <div style="font-size:11.5px;color:#94a3b8;margin-top:4px;" id="unlockNote"></div>
      </div>
      <div class="actions">
        <button type="button" class="btn-secondary" onclick="copyOtp()">نسخ الكود</button>
        <button type="button" class="btn-danger" onclick="clearOtp()">إلغاء الكود</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    let selectedBox = "box_1";
    let selectedDuration = 10;
    let currentOtp = "";
    let countdownInterval = null;

    function showToast(msg) {
      const t = document.getElementById("toast");
      t.innerText = msg;
      t.classList.add("show");
      setTimeout(() => t.classList.remove("show"), 2200);
    }

    function selectBox(boxId) {
      selectedBox = boxId;
      document.getElementById("selectedBoxLabel").innerText = boxId;
      document.getElementById("card_box_1").classList.toggle("active", boxId === "box_1");
      document.getElementById("card_box_2").classList.toggle("active", boxId === "box_2");
      refreshStatus();
    }

    function setDuration(sec) {
      selectedDuration = Math.max(2, Math.min(60, Number(sec) || 10));
      document.getElementById("durationSlider").value = selectedDuration;
      document.getElementById("durationBadge").innerText = `${selectedDuration} ث`;
      document.querySelectorAll("#presetChips .chip").forEach((btn) => {
        const val = parseInt(btn.innerText, 10);
        btn.classList.toggle("selected", val === selectedDuration);
      });
    }

    function startCountdown(secondsLeft) {
      if (countdownInterval) clearInterval(countdownInterval);
      let rem = Math.max(0, Math.floor(secondsLeft));
      const updateText = () => {
        const m = String(Math.floor(rem / 60)).padStart(2, "0");
        const s = String(rem % 60).padStart(2, "0");
        document.getElementById("resTimer").innerText = `صلاحية الكود: ${m}:${s}`;
        if (rem <= 0) {
          clearInterval(countdownInterval);
          document.getElementById("resTimer").innerText = "انتهت صلاحية الكود";
          refreshStatus();
        }
        rem -= 1;
      };
      updateText();
      countdownInterval = setInterval(updateText, 1000);
    }

    async function generateCode() {
      const btn = document.getElementById("genBtn");
      btn.disabled = true;
      btn.innerText = "جاري التوليد والربط...";

      const phone = document.getElementById("phoneInput").value.trim();

      try {
        const res = await fetch("/api/generate-otp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            box_id: selectedBox,
            duration_sec: selectedDuration,
            duration_label: `${selectedDuration} ثانية`,
            phone: phone || null
          })
        });
        const data = await res.json();

        if (data.success) {
          currentOtp = data.otp;
          document.getElementById("resultCard").style.display = "block";
          document.getElementById("resBoxInfo").innerText = `مفعّل على: ${data.box_id}`;
          document.getElementById("otpValue").innerText = data.otp;
          document.getElementById("keypadSeq").innerText = `${data.otp}#`;
          document.getElementById("unlockNote").innerText =
            `سيفتح القفل لمدة ${data.duration_sec} ثوانٍ فور التحقق من السيرفر`;
          startCountdown(data.expires_in || 600);
          showToast(`تم تفعيل الكود ${data.otp} لـ ${data.box_id}`);
          await refreshStatus();
        } else {
          showToast(data.message || "تعذر توليد الكود");
        }
      } catch (err) {
        showToast("خطأ في الاتصال بالسيرفر");
      } finally {
        btn.disabled = false;
        btn.innerText = "توليد وتفعيل كود OTP الآن";
      }
    }

    async function clearOtp() {
      try {
        const res = await fetch("/api/clear-otp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ box_id: selectedBox })
        });
        const data = await res.json();
        if (data.success) {
          currentOtp = "";
          if (countdownInterval) clearInterval(countdownInterval);
          document.getElementById("resultCard").style.display = "none";
          showToast(`تم إلغاء كود ${selectedBox}`);
          await refreshStatus();
        }
      } catch (e) {
        showToast("تعذر إلغاء الكود");
      }
    }

    function copyOtp() {
      if (!currentOtp) return;
      navigator.clipboard?.writeText(currentOtp);
      showToast(`تم نسخ الكود ${currentOtp}`);
    }

    async function refreshStatus() {
      try {
        const res = await fetch("/api/status");
        const data = await res.json();
        for (const [boxId, info] of Object.entries(data.boxes || {})) {
          const pill = document.getElementById(`pill_${boxId}`);
          const meta = document.getElementById(`meta_${boxId}`);
          if (!pill || !meta) continue;
          if (info.has_otp) {
            pill.innerText = `نشط (${info.unlock_seconds}ث)`;
            pill.className = "pill active-otp";
            meta.innerText = `كود: ${info.otp_masked || "****"} • مدة الفتح ${info.unlock_seconds}ث`;
          } else {
            pill.innerText = "فارغ";
            pill.className = "pill";
            meta.innerText = `المعرف: ${boxId} • جاهز للاستقبال`;
          }
        }
      } catch (e) {}
    }

    refreshStatus();
    setInterval(refreshStatus, 4000);
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
        otp_val = info.get("otp")
        valid = bool(otp_val) and now <= info.get("expires_at", 0)
        summary[box_id] = {
            "has_otp": valid,
            "unlock_seconds": info.get("unlock_seconds", 5),
            "otp_masked": f"{otp_val[:1]}***" if valid and otp_val else None,
        }
    return jsonify({"status": "online", "boxes": summary}), 200


@app.route("/api/clear-otp", methods=["POST"])
def clear_otp():
    data = request.get_json(silent=True) or {}
    box_id = normalize_box_id(data.get("box_id") or data.get("boxId") or data.get("box"))
    if not box_id or box_id not in boxes_db:
        return jsonify({"success": False, "message": "Unknown Box"}), 400

    boxes_db[box_id]["otp"] = None
    boxes_db[box_id]["expires_at"] = 0
    return jsonify({"success": True, "box_id": box_id, "message": "OTP cleared"}), 200


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
        "expires_in": ttl_seconds,
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
