from flask import Flask, request, jsonify, render_template_string
import random
import time
import os
import requests

app = Flask(__name__)

# قاعدة بيانات مؤقتة في الذاكرة لإدارة الصندوقين بشكل مستقل
boxes_db = {
    "box_1": {"otp": None, "expires_at": 0, "phone": None},
    "box_2": {"otp": None, "expires_at": 0, "phone": None}
}

# قراءة المفاتيح السرية من Environment Variables في Render بأمان
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
ESP_API_KEY = os.environ.get("ESP_API_KEY", "")

def send_whatsapp_message(phone, box_name, otp, hours):
    if not WHATSAPP_API_URL or not WHATSAPP_TOKEN or not phone:
        print(f"[WhatsApp Simulation] To: {phone} | Box: {box_name} | OTP: {otp} | Hours: {hours}")
        return False
    
    message = (
        f"أهلاً بك في نظام الصناديق الذكية 📦\n"
        f"تم تأكيد حجزك بنجاح!\n"
        f"• الصندوق: {box_name}\n"
        f"• مدة الإيجار: {hours} ساعة\n"
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
            --surface: #334155;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --accent: #10b981;
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
            max-width: 480px;
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
        .header h1 { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }
        .header p { margin: 6px 0 0; color: var(--text-muted); font-size: 14px; }

        .section-title { font-size: 14px; font-weight: 700; color: #cbd5e1; margin: 18px 0 10px; }

        /* بطاقات اختيار الصندوق */
        .lockers-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .locker-option {
            background: rgba(15, 23, 42, 0.6);
            border: 2px solid var(--border);
            border-radius: 16px;
            padding: 16px 12px;
            text-align: center;
            cursor: pointer;
            transition: all 0.25s ease;
            position: relative;
        }
        .locker-option:hover { border-color: #475569; transform: translateY(-2px); }
        .locker-option.active {
            border-color: var(--primary);
            background: rgba(59, 130, 246, 0.12);
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
        }
        .locker-icon { font-size: 28px; margin-bottom: 6px; display: block; }
        .locker-name { font-weight: 700; font-size: 15px; display: block; }
        .locker-status {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 6px;
            display: inline-block;
            margin-top: 6px;
            font-weight: 600;
        }
        .status-free { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .status-busy { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

        /* أزرار المدة */
        .duration-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .dur-btn {
            background: rgba(15, 23, 42, 0.6);
            border: 1.5px solid var(--border);
            color: var(--text-main);
            border-radius: 12px;
            padding: 10px 4px;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s;
        }
        .dur-btn.active {
            border-color: var(--primary);
            background: var(--primary);
            color: white;
        }
        .dur-time { font-weight: 700; font-size: 13px; display: block; }
        .dur-price { font-size: 11px; opacity: 0.85; }

        /* حقل الجوال */
        .input-group { position: relative; }
        .input-group input {
            width: 100%;
            background: rgba(15, 23, 42, 0.8);
            border: 1.5px solid var(--border);
            color: white;
            padding: 14px 16px;
            border-radius: 14px;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
            direction: ltr;
            text-align: left;
        }
        .input-group input:focus { border-color: var(--primary); }

        /* زر الدفع */
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
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .pay-btn:hover { transform: translateY(-2px); box-shadow: 0 14px 24px -5px rgba(37, 99, 235, 0.5); }
        .pay-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

        /* بطاقة النتيجة والتذكرة */
        .ticket {
            margin-top: 24px;
            background: linear-gradient(145deg, rgba(16, 185, 129, 0.15), rgba(6, 95, 70, 0.25));
            border: 1.5px dashed #10b981;
            border-radius: 18px;
            padding: 20px;
            text-align: center;
            display: none;
            animation: fadeIn 0.4s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .ticket-title { color: #34d399; font-weight: 700; font-size: 15px; margin-bottom: 6px; }
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
            <p>احجز خزنتك إلكترونياً واستلم رمز الفتح الفوري</p>
        </div>

        <div class="section-title">1. اختر الخزنة المطلوبة:</div>
        <div class="lockers-grid">
            <div class="locker-option active" id="card_box_1" onclick="selectBox('box_1')">
                <span class="locker-icon">🔐</span>
                <span class="locker-name">الخزنة الأولى (Box 1)</span>
                <span class="locker-status status-free" id="status_box_1">● متاح للحجز</span>
            </div>
            <div class="locker-option" id="card_box_2" onclick="selectBox('box_2')">
                <span class="locker-icon">🔐</span>
                <span class="locker-name">الخزنة الثانية (Box 2)</span>
                <span class="locker-status status-free" id="status_box_2">● متاح للحجز</span>
            </div>
        </div>

        <div class="section-title">2. حدد مدة الإيجار:</div>
        <div class="duration-grid">
            <div class="dur-btn active" onclick="selectDuration(this, 1, 10)">
                <span class="dur-time">1 ساعة</span>
                <span class="dur-price">10 ر.س</span>
            </div>
            <div class="dur-btn" onclick="selectDuration(this, 2, 18)">
                <span class="dur-time">2 ساعة</span>
                <span class="dur-price">18 ر.س</span>
            </div>
            <div class="dur-btn" onclick="selectDuration(this, 5, 40)">
                <span class="dur-time">5 ساعات</span>
                <span class="dur-price">40 ر.س</span>
            </div>
            <div class="dur-btn" onclick="selectDuration(this, 24, 80)">
                <span class="dur-time">24 ساعة</span>
                <span class="dur-price">80 ر.س</span>
            </div>
        </div>

        <div class="section-title">3. رقم الواتساب لاستلام الرمز:</div>
        <div class="input-group">
            <input type="tel" id="phone" placeholder="9665XXXXXXXX" value="9665">
        </div>

        <button class="pay-btn" id="submitBtn" onclick="rentBox()">
            💳 تأكيد ودفع (10 ر.س)
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
        let selectedHours = 1;
        let selectedPrice = 10;
        let currentGeneratedOtp = '';

        function selectBox(boxId) {
            selectedBox = boxId;
            document.querySelectorAll('.locker-option').forEach(el => el.classList.remove('active'));
            document.getElementById('card_' + boxId).classList.add('active');
        }

        function selectDuration(btn, hours, price) {
            selectedHours = hours;
            selectedPrice = price;
            document.querySelectorAll('.dur-btn').forEach(el => el.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('submitBtn').innerText = `💳 تأكيد ودفع (${price} ر.س)`;
        }

        async function rentBox() {
            const phone = document.getElementById('phone').value.trim();
            const btn = document.getElementById('submitBtn');

            if (phone.length < 10) {
                alert("يرجى إدخال رقم واتساب صحيح مع رمز الدولة (مثال: 9665XXXXXXXX)");
                return;
            }

            btn.disabled = true;
            btn.innerText = "⏳ جاري معالجة الطلب وتوليد الرمز...";

            try {
                const res = await fetch('/api/generate-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ box_id: selectedBox, hours: selectedHours, phone: phone })
                });

                const data = await res.json();
                if (data.status === 'success') {
                    currentGeneratedOtp = data.otp;
                    document.getElementById('resultBox').style.display = 'block';
                    document.getElementById('otpDisplay').innerText = data.otp;
                    
                    const boxArabic = selectedBox === 'box_1' ? 'الخزنة الأولى (Box 1)' : 'الخزنة الثانية (Box 2)';
                    document.getElementById('infoDisplay').innerHTML = 
                        `تم تخصيص <b>${boxArabic}</b> لمدة <b>${selectedHours} ساعة</b><br>أدخل الرمز أعلاه في لوحة المفاتيح لفتح القفل`;

                    const statusBadge = document.getElementById('status_' + selectedBox);
                    statusBadge.className = 'locker-status status-busy';
                    statusBadge.innerText = '● نشط حالياً';
                } else {
                    alert("حدث خطأ: " + data.message);
                }
            } catch (err) {
                alert("تعذر الاتصال بالسيرفر، تأكد من الإنترنت.");
            } finally {
                btn.disabled = false;
                btn.innerText = `💳 تأكيد ودفع (${selectedPrice} ر.س)`;
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

@app.route('/api/generate-otp', methods=['POST'])
def generate_otp():
    data = request.get_json(silent=True) or {}
    box_id = data.get('box_id', 'box_1')
    hours = float(data.get('hours', 1))
    phone = data.get('phone', '')

    if box_id not in boxes_db:
        return jsonify({"status": "error", "message": "Invalid box_id"}), 400

    new_otp = str(random.randint(1000, 9999))
    expiry_timestamp = time.time() + (hours * 3600)

    boxes_db[box_id] = {
        "otp": new_otp,
        "expires_at": expiry_timestamp,
        "phone": phone
    }

    box_label = "الصندوق الأول (Box 1)" if box_id == "box_1" else "الصندوق الثاني (Box 2)"
    send_whatsapp_message(phone, box_label, new_otp, hours)

    print(f"[{box_id}] New OTP: {new_otp} | Valid for: {hours}h")
    return jsonify({
        "status": "success",
        "box_id": box_id,
        "otp": new_otp,
        "expires_in_hours": hours
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
