from flask import Flask, request, jsonify, render_template_string
import random
import time
import os
import requests

app = Flask(__name__)

# قاعدة بيانات مؤقتة لإدارة الصندوقين بالوقت الفعلي
boxes_db = {
    "box_1": {"otp": None, "expires_at": 0, "phone": None},
    "box_2": {"otp": None, "expires_at": 0, "phone": None}
}

WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
ESP_API_KEY = os.environ.get("ESP_API_KEY", "")

def send_whatsapp_message(phone, box_name, otp, duration_label):
    if not WHATSAPP_API_URL or not WHATSAPP_TOKEN or not phone:
        print(f"[WhatsApp Simulation] To: {phone} | Box: {box_name} | OTP: {otp} | Duration: {duration_label}")
        return False
    
    message = (
        f"أهلاً بك في نظام الصناديق الذكية 📦\n"
        f"تم تأكيد حجزك بنجاح!\n"
        f"• الصندوق: {box_name}\n"
        f"• مدة الإيجار: {duration_label}\n"
        f"• رمز الفتح السري (OTP): *{otp}*\n"
        f"يرجى إدخال الرمز في لوحة الصندوق للفتح."
    )
    payload = {
        "token": WHATSAPP_TOKEN,
        "to": phone,
        "body": message
    }
    try:
        response = requests.post(WHATSAPP_API_URL, data=payload, timeout=5)
        print("WhatsApp API Response:", response.text)
        return True
    except Exception as e:
        print("WhatsApp Error:", e)
        return False

STORE_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Locker | نظام الصناديق الذكية</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --primary: #3b82f6;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
        }
        * { box-sizing: border-box; font-family: 'Cairo', sans-serif; }
        body {
            background: radial-gradient(circle at top, #1e293b 0%, #0f172a 100%);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .app-card {
            width: 100%;
            max-width: 500px;
            background: var(--card-bg);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            padding: 28px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .header { text-align: center; margin-bottom: 24px; }
        .badge {
            display: inline-block;
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            padding: 4px 14px;
            border-radius: 99px;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .header h1 { margin: 0; font-size: 24px; font-weight: 800; }
        .header p { margin: 6px 0 0; color: var(--text-muted); font-size: 14px; }
        .section-title { font-size: 14px; font-weight: 700; color: #cbd5e1; margin: 18px 0 10px; }

        .lockers-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .locker-option {
            background: rgba(15, 23, 42, 0.6);
            border: 2px solid var(--border);
            border-radius: 16px;
            padding: 16px 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.25s ease;
        }
        .locker-option:hover:not(.locked) { border-color: #475569; transform: translateY(-2px); }
        .locker-option.active {
            border-color: var(--primary);
            background: rgba(59, 130, 246, 0.12);
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
        }
        .locker-option.locked {
            opacity: 0.75;
            border-color: rgba(239, 68, 68, 0.4);
            background: rgba(239, 68, 68, 0.06);
        }
        .locker-icon { font-size: 28px; margin-bottom: 6px; display: block; }
        .locker-name { font-weight: 700; font-size: 15px; display: block; }
        .locker-status {
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 6px;
            display: inline-block;
            margin-top: 6px;
            font-weight: 700;
        }
        .status-free { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .status-busy { background: rgba(239, 68, 68, 0.18); color: #f87171; }
        .timer-text { display: block; font-size: 11px; color: #fbbf24; margin-top: 4px; font-weight: 600; direction: ltr; }

        .duration-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
        .dur-btn {
            background: rgba(15, 23, 42, 0.6);
            border: 1.5px solid var(--border);
            color: var(--text-main);
            border-radius: 12px;
            padding: 10px 2px;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s;
        }
        .dur-btn.active { border-color: var(--primary); background: var(--primary); color: white; }
        .dur-time { font-weight: 700; font-size: 12px; display: block; }
        .dur-price { font-size: 10px; opacity: 0.85; }

        .input-group input {
            width: 100%;
            background: rgba(15, 23, 42, 0.8);
            border: 1.5px solid var(--border);
            color: white;
            padding: 14px 16px;
            border-radius: 14px;
            font-size: 15px;
            outline: none;
            direction: ltr;
            text-align: left;
        }
        .input-group input:focus { border-color: var(--primary); }

        .pay-btn {
            width: 100%;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            border: none;
            padding: 15px;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 22px;
            box-shadow: 0 10px 20px -5px rgba(37, 99, 235, 0.4);
            transition: all 0.2s;
        }
        .pay-btn:hover:not(:disabled) { transform: translateY(-2px); }
        .pay-btn:disabled { background: #475569; box-shadow: none; cursor: not-allowed; opacity: 0.7; }

        .ticket {
            margin-top: 24px;
            background: linear-gradient(145deg, rgba(16, 185, 129, 0.15), rgba(6, 95, 70, 0.25));
            border: 1.5px dashed #10b981;
            border-radius: 18px;
            padding: 20px;
            text-align: center;
            display: none;
        }
        .ticket-title { color: #34d399; font-weight: 700; font-size: 15px; }
        .otp-box {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 12px;
            padding: 12px;
            margin: 12px 0;
            font-size: 34px;
            font-weight: 800;
            letter-spacing: 8px;
            color: #fff;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .ticket-meta { font-size: 13px; color: #cbd5e1; line-height: 1.6; }
        .copy-btn {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
            padding: 6px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="app-card">
        <div class="header">
            <span class="badge">IoT Smart Delivery & Storage</span>
            <h1>📦 الخزائن الذكية</h1>
            <p>نظام حجز فوري بالوقت الفعلي</p>
        </div>

        <div class="section-title">1. اختر الخزنة المطلوبة:</div>
        <div class="lockers-grid">
            <div class="locker-option active" id="card_box_1" onclick="selectBox('box_1')">
                <span class="locker-icon" id="icon_box_1">🔓</span>
                <span class="locker-name">الخزنة الأولى (Box 1)</span>
                <span class="locker-status status-free" id="status_box_1">● متاح للحجز</span>
                <span class="timer-text" id="timer_box_1"></span>
            </div>
            <div class="locker-option" id="card_box_2" onclick="selectBox('box_2')">
                <span class="locker-icon" id="icon_box_2">🔓</span>
                <span class="locker-name">الخزنة الثانية (Box 2)</span>
                <span class="locker-status status-free" id="status_box_2">● متاح للحجز</span>
                <span class="timer-text" id="timer_box_2"></span>
            </div>
        </div>

        <div class="section-title">2. حدد مدة الإيجار:</div>
        <div class="duration-grid">
            <div class="dur-btn active" onclick="selectDuration(this, 5, 2, '5 دقائق')">
                <span class="dur-time">5 دقائق</span>
                <span class="dur-price">2 ر.س</span>
            </div>
            <div class="dur-btn" onclick="selectDuration(this, 60, 10, 'ساعة واحدة')">
                <span class="dur-time">1 ساعة</span>
                <span class="dur-price">10 ر.س</span>
            </div>
            <div class="dur-btn" onclick="selectDuration(this, 120, 18, 'ساعتان')">
                <span class="dur-time">2 ساعة</span>
                <span class="dur-price">18 ر.س</span>
            </div>
            <div class="dur-btn" onclick="selectDuration(this, 300, 40, '5 ساعات')">
                <span class="dur-time">5 ساعات</span>
                <span class="dur-price">40 ر.س</span>
            </div>
            <div class="dur-btn" onclick="selectDuration(this, 1440, 80, '24 ساعة')">
                <span class="dur-time">24 ساعة</span>
                <span class="dur-price">80 ر.س</span>
            </div>
        </div>

        <div class="section-title">3. رقم الواتساب لاستلام الرمز:</div>
        <div class="input-group">
            <input type="tel" id="phone" placeholder="9665XXXXXXXX" value="9665">
        </div>

        <button class="pay-btn" id="submitBtn" onclick="rentBox()">
            💳 تأكيد ودفع (2 ر.س)
        </button>

        <div class="ticket" id="resultBox">
            <div class="ticket-title">✅ تم تفعيل الخزنة بنجاح!</div>
            <div class="otp-box" id="otpDisplay">----</div>
            <div class="ticket-meta" id="infoDisplay"></div>
            <button class="copy-btn" onclick="copyOtp()">📋 نسخ رمز الفتح</button>
        </div>
    </div>

    <script>
        let selectedBox = 'box_1';
        let selectedMinutes = 5;
        let selectedPrice = 2;
        let selectedLabel = '5 دقائق';
        let currentGeneratedOtp = '';
        let boxesState = {
            box_1: { active: false, remaining_seconds: 0 },
            box_2: { active: false, remaining_seconds: 0 }
        };

        function selectBox(boxId) {
            selectedBox = boxId;
            document.querySelectorAll('.locker-option').forEach(el => el.classList.remove('active'));
            document.getElementById('card_' + boxId).classList.add('active');
            updatePayButton();
        }

        function selectDuration(btn, minutes, price, label) {
            selectedMinutes = minutes;
            selectedPrice = price;
            selectedLabel = label;
            document.querySelectorAll('.dur-btn').forEach(el => el.classList.remove('active'));
            btn.classList.add('active');
            updatePayButton();
        }

        function updatePayButton() {
            const btn = document.getElementById('submitBtn');
            if (boxesState[selectedBox].active) {
                btn.disabled = true;
                btn.innerText = "🔒 هذه الخزنة محجوزة حالياً";
            } else {
                btn.disabled = false;
                btn.innerText = `💳 تأكيد ودفع (${selectedPrice} ر.س)`;
            }
        }

        function formatSeconds(sec) {
            if (sec <= 0) return "";
            const h = Math.floor(sec / 3600);
            const m = Math.floor((sec % 3600) / 60);
            const s = Math.floor(sec % 60);
            if (h > 0) return `⏳ ${h}h ${m}m ${s}s`;
            return `⏳ ${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        }

        function renderBoxesUI() {
            ['box_1', 'box_2'].forEach(id => {
                const state = boxesState[id];
                const card = document.getElementById('card_' + id);
                const icon = document.getElementById('icon_' + id);
                const status = document.getElementById('status_' + id);
                const timer = document.getElementById('timer_' + id);

                if (state.active && state.remaining_seconds > 0) {
                    card.classList.add('locked');
                    icon.innerText = '🔒';
                    status.className = 'locker-status status-busy';
                    status.innerText = '● محجوز حالياً';
                    timer.innerText = formatSeconds(state.remaining_seconds);
                } else {
                    state.active = false;
                    card.classList.remove('locked');
                    icon.innerText = '🔓';
                    status.className = 'locker-status status-free';
                    status.innerText = '● متاح للحجز';
                    timer.innerText = '';
                }
            });
            updatePayButton();
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                boxesState = data;
                renderBoxesUI();
            } catch (e) {}
        }

        // تحديث العداد كل ثانية محلياً ومزامنته مع السيرفر كل 10 ثوانٍ
        setInterval(() => {
            ['box_1', 'box_2'].forEach(id => {
                if (boxesState[id].active && boxesState[id].remaining_seconds > 0) {
                    boxesState[id].remaining_seconds -= 1;
                }
            });
            renderBoxesUI();
        }, 1000);

        setInterval(fetchStatus, 10000);
        fetchStatus();

        async function rentBox() {
            if (boxesState[selectedBox].active) return;

            const phone = document.getElementById('phone').value.trim();
            const btn = document.getElementById('submitBtn');

            if (phone.length < 10) {
                alert("يرجى إدخال رقم واتساب صحيح مع رمز الدولة (مثال: 9665XXXXXXXX)");
                return;
            }

            btn.disabled = true;
            btn.innerText = "⏳ جاري تفعيل الحجز...";

            try {
                const res = await fetch('/api/generate-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        box_id: selectedBox,
                        minutes: selectedMinutes,
                        duration_label: selectedLabel,
                        phone: phone
                    })
                });

                const data = await res.json();
                if (data.status === 'success') {
                    currentGeneratedOtp = data.otp;
                    document.getElementById('resultBox').style.display = 'block';
                    document.getElementById('otpDisplay').innerText = data.otp;
                    
                    const boxArabic = selectedBox === 'box_1' ? 'الخزنة الأولى (Box 1)' : 'الخزنة الثانية (Box 2)';
                    document.getElementById('infoDisplay').innerHTML = 
                        `تم تخصيص <b>${boxArabic}</b> لمدة <b>${selectedLabel}</b><br>أدخل الرمز في لوحة المفاتيح قبل انتهاء العداد`;

                    await fetchStatus();
                } else {
                    alert(data.message);
                    await fetchStatus();
                }
            } catch (err) {
                alert("تعذر الاتصال بالسيرفر.");
                updatePayButton();
            }
        }

        function copyOtp() {
            if (!currentGeneratedOtp) return;
            navigator.clipboard.writeText(currentGeneratedOtp);
            alert("تم نسخ الرمز: " + currentGeneratedOtp);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(STORE_HTML)

# مسار جديد لإرجاع الحالة الحقيقية للصندوقين والوقت المتبقي
@app.route('/api/status', methods=['GET'])
def get_status():
    now = time.time()
    status_data = {}
    for box_id, info in boxes_db.items():
        remaining = max(0, int(info["expires_at"] - now))
        is_active = bool(info["otp"] and remaining > 0)
        status_data[box_id] = {
            "active": is_active,
            "remaining_seconds": remaining
        }
    return jsonify(status_data), 200

@app.route('/api/generate-otp', methods=['POST'])
def generate_otp():
    data = request.get_json(silent=True) or {}
    box_id = data.get('box_id', 'box_1')
    minutes = float(data.get('minutes', 5))
    duration_label = data.get('duration_label', f'{int(minutes)} دقيقة')
    phone = data.get('phone', '')

    if box_id not in boxes_db:
        return jsonify({"status": "error", "message": "Invalid box_id"}), 400

    now = time.time()
    # منع الحجز المزدوج إذا كانت الخزنة لا تزال نشطة
    if boxes_db[box_id]["otp"] and now < boxes_db[box_id]["expires_at"]:
        return jsonify({"status": "error", "message": "عذراً، هذه الخزنة محجوزة حالياً ولم ينتهِ وقتها بعد!"}), 409

    new_otp = str(random.randint(1000, 9999))
    expiry_timestamp = now + (minutes * 60)

    boxes_db[box_id] = {
        "otp": new_otp,
        "expires_at": expiry_timestamp,
        "phone": phone
    }

    box_label = "الصندوق الأول (Box 1)" if box_id == "box_1" else "الصندوق الثاني (Box 2)"
    send_whatsapp_message(phone, box_label, new_otp, duration_label)

    print(f"[{box_id}] New OTP: {new_otp} | Valid for: {minutes} mins")
    return jsonify({
        "status": "success",
        "box_id": box_id,
        "otp": new_otp,
        "expires_in_minutes": minutes
    }), 200

@app.route('/api/verify', methods=['POST'])
def verify_code():
    if ESP_API_KEY:
        client_key = request.headers.get('X-API-KEY', '')
        if client_key != ESP_API_KEY:
            print("Unauthorized ESP32 Request!")
            return jsonify({"status": "denied", "message": "Unauthorized Device"}), 401

    data = request.get_json(silent=True) or {}
    box_id = data.get('box_id', 'box_1')
    entered_code = str(data.get('code', '')).strip()

    if box_id not in boxes_db:
        return jsonify({"status": "denied", "message": "Unknown Box"}), 400

    box_info = boxes_db[box_id]
    current_time = time.time()

    if box_info["otp"] and entered_code == box_info["otp"]:
        if current_time <= box_info["expires_at"]:
            print(f"[{box_id}] Access Granted!")
            return jsonify({"status": "open", "message": "Access Granted"}), 200
        else:
            print(f"[{box_id}] Access Denied: OTP Expired!")
            return jsonify({"status": "denied", "message": "OTP Expired"}), 403
    else:
        print(f"[{box_id}] Access Denied: Wrong OTP!")
        return jsonify({"status": "denied", "message": "Invalid OTP"}), 401

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
