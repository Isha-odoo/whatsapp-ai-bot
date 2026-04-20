from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests

app = Flask(__name__)

# =========================
# ODOO CONFIG
# =========================
ODOO_URL = "https://edu-isha1.odoo.com"
ODOO_DB = "edu-isha1"
ODOO_USERNAME = "mais@odoo.com"
ODOO_PASSWORD = "123456"

# =========================
# SESSION STORAGE
# =========================
sessions = {}

# =========================
# CREATE ODOO LEAD
# =========================
def create_odoo_lead(data):
    try:
        # Authenticate
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

        auth = requests.post(f"{ODOO_URL}/jsonrpc", json=auth_payload).json()
        uid = auth.get("result")

        if not uid:
            print("❌ Odoo Auth Failed")
            return

        # Create Lead
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
                        "name": f"Website Inquiry - {data.get('name')}",
                        "contact_name": data.get("name"),
                        "email_from": data.get("email"),
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

        lead = requests.post(f"{ODOO_URL}/jsonrpc", json=lead_payload).json()
        print("✅ Lead Created:", lead)

    except Exception as e:
        print("❌ Error creating lead:", e)

# =========================
# WHATSAPP BOT FLOW
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    user = request.values.get("From")
    msg = request.values.get("Body", "").strip()

    print(f"{user}: {msg}")

    state = sessions.get(user, {"step": 0})
    reply = ""

    if state["step"] == 0:
        reply = "👋 Hi! Welcome.\nWhat is your *full name*?"
        state["step"] = 1

    elif state["step"] == 1:
        state["name"] = msg
        reply = "📧 Please enter your email address:"
        state["step"] = 2

    elif state["step"] == 2:
        state["email"] = msg
        reply = "💼 What service do you need?"
        state["step"] = 3

    elif state["step"] == 3:
        state["service"] = msg
        reply = "💰 What is your budget?"
        state["step"] = 4

    elif state["step"] == 4:
        state["budget"] = msg
        reply = "🌐 Do you have a website? (yes/no)"
        state["step"] = 5

    elif state["step"] == 5:
        state["has_website"] = msg.lower()

        if msg.lower() in ["yes", "y"]:
            reply = "🔗 Please share your website link:"
            state["step"] = 6
        else:
            state["website_link"] = "No Website"

            print("🔥 FINAL DATA:", state)
            create_odoo_lead(state)   # ✅ CREATE LEAD

            reply = "✅ Thank you! Our team will contact you soon."
            sessions.pop(user, None)

    elif state["step"] == 6:
        state["website_link"] = msg

        print("🔥 FINAL DATA:", state)
        create_odoo_lead(state)   # ✅ CREATE LEAD

        reply = "✅ Thank you! Our team will contact you soon."
        sessions.pop(user, None)

    sessions[user] = state

    resp = MessagingResponse()
    resp.message(reply)

    return str(resp)

# =========================
# HEALTH CHECK
# =========================
@app.route("/")
def home():
    return "Bot Running ✅"

@app.route("/ping")
def ping():
    return "alive"

if __name__ == "__main__":
    app.run(debug=True)
