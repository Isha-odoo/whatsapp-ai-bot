from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import threading

app = Flask(__name__)

# =========================
# 🔐 ODOO CONFIG
# =========================
ODOO_URL = "https://your-odoo.com"
ODOO_DB = "your_db"
ODOO_USERNAME = "your@email.com"
ODOO_PASSWORD = "your_password"

# =========================
# 🧠 SESSION STORE
# =========================
sessions = {}

# =========================
# 🚀 SAFE ODOO CALL
# =========================
def create_odoo_lead(data):
    try:
        print("🚀 Sending to Odoo:", data)

        auth_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]
            },
            "id": 1
        }

        auth = requests.post(
            f"{ODOO_URL}/jsonrpc",
            json=auth_payload,
            timeout=5   # 🔥 prevent hanging
        ).json()

        uid = auth.get("result")
        if not uid:
            print("❌ Auth failed")
            return

        lead_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "crm.lead",
                    "create",
                    [{
                        "name": f"WhatsApp Lead - {data.get('name')}",
                        "contact_name": data.get("name"),
                        "email_from": data.get("email"),
                        "phone": data.get("phone"),
                        "description": f"""
Service: {data.get('service')}
Budget: {data.get('budget')}
Has Website: {data.get('has_website')}
Website: {data.get('website_link')}
                        """
                    }]
                ]
            },
            "id": 2
        }

        res = requests.post(
            f"{ODOO_URL}/jsonrpc",
            json=lead_payload,
            timeout=5   # 🔥 prevent hanging
        ).json()

        print("✅ Lead created:", res)

    except Exception as e:
        print("❌ Odoo error:", e)


# =========================
# 📲 WHATSAPP BOT
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    print("🔥 HIT /whatsapp")

    from twilio.twiml.messaging_response import MessagingResponse

    try:
        msg = request.values.get("Body", "").strip()
        print("Incoming:", msg)

        resp = MessagingResponse()
        resp.message("✅ Bot is working")

        # 🔥 ALWAYS return immediately
        return str(resp)

    except Exception as e:
        print("❌ ERROR:", e)

        resp = MessagingResponse()
        resp.message("⚠️ Error occurred")

        return str(resp)

# =========================
# 🟢 HEALTH CHECK
# =========================
@app.route("/")
def home():
    return "Bot Running ✅"

@app.route("/ping")
def ping():
    return "alive"


# =========================
# ▶ RUN
# =========================
if __name__ == "__main__":
    app.run()
