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
    try:
        print("🔥 HIT /whatsapp")

        user = request.values.get("From")
        msg = request.values.get("Body", "").strip()

        print(f"{user}: {msg}")

        state = sessions.get(user, {"step": 0})
        reply = ""

        # FLOW
        if state["step"] == 0:
            reply = "👋 Hi! What is your full name?"
            state["step"] = 1

        elif state["step"] == 1:
            state["name"] = msg
            reply = "📧 Enter your email:"
            state["step"] = 2

        elif state["step"] == 2:
            state["email"] = msg
            reply = "📞 Enter your phone number:"
            state["step"] = 3

        elif state["step"] == 3:
            state["phone"] = msg
            reply = "💼 What service do you need?"
            state["step"] = 4

        elif state["step"] == 4:
            state["service"] = msg
            reply = "💰 What is your budget?"
            state["step"] = 5

        elif state["step"] == 5:
            state["budget"] = msg
            reply = "🌐 Do you have a website? (yes/no)"
            state["step"] = 6

        elif state["step"] == 6:
            state["has_website"] = msg.lower()

            if msg.lower() in ["yes", "y"]:
                reply = "🔗 Share your website link:"
                state["step"] = 7
            else:
                state["website_link"] = "No Website"

                lead_data = state.copy()
                sessions.pop(user, None)

                resp = MessagingResponse()
                resp.message("✅ Thank you! We'll contact you soon.")

                # 🚀 background thread (non-blocking)
                threading.Thread(
                    target=create_odoo_lead,
                    args=(lead_data,),
                    daemon=True
                ).start()

                return str(resp)

        elif state["step"] == 7:
            state["website_link"] = msg

            lead_data = state.copy()
            sessions.pop(user, None)

            resp = MessagingResponse()
            resp.message("✅ Thank you! We'll contact you soon.")

            threading.Thread(
                target=create_odoo_lead,
                args=(lead_data,),
                daemon=True
            ).start()

            return str(resp)

        sessions[user] = state

        resp = MessagingResponse()
        resp.message(reply)

        return str(resp)

    except Exception as e:
        print("❌ CRASH:", e)

        # 🔥 ALWAYS RETURN RESPONSE (even on error)
        resp = MessagingResponse()
        resp.message("⚠️ Something went wrong. Please try again.")

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
