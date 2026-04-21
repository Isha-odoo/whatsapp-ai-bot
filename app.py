from flask import Flask, request
import requests
import os

app = Flask(__name__)

# =========================
# CONFIG (FROM RENDER ENV)
# =========================
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "abc123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

# =========================
# SESSION STORAGE
# =========================
sessions = {}

# =========================
# WEBHOOK VERIFY (META)
# =========================
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge, 200

    return "Invalid token", 403

# =========================
# RECEIVE MESSAGE (META)
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" in value:
            msg = value["messages"][0]
            phone = msg["from"]
            text = msg["text"]["body"]

            print(f"{phone}: {text}")

            handle_message(phone, text)

    except Exception as e:
        print("Error:", e)

    return "ok"

# =========================
# SEND MESSAGE (META API)
# =========================
def send_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    res = requests.post(url, headers=headers, json=payload)
    print("Send:", res.text)

# =========================
# CREATE ODOO LEAD
# =========================
def create_odoo_lead(data):
    try:
        # LOGIN
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
            print("Odoo Auth Failed")
            return

        # CREATE LEAD
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
                        "name": f"WhatsApp Inquiry - {data.get('name')}",
                        "contact_name": data.get("name"),
                        "email_from": data.get("email"),
                        "phone": data.get("phone"),
                        "description": f"""
Service: {data.get('service')}
Budget: {data.get('budget')}
Website: {data.get('website_link')}
                        """
                    }]
                ]
            },
            "id": 2
        }

        res = requests.post(f"{ODOO_URL}/jsonrpc", json=lead_payload).json()
        print("Lead Created:", res)

    except Exception as e:
        print("Odoo Error:", e)

# =========================
# BOT FLOW
# =========================
def handle_message(user, msg):
    state = sessions.get(user, {"step": 0, "phone": user})
    reply = ""

    if state["step"] == 0:
        reply = "👋 Hi! What is your full name?"
        state["step"] = 1

    elif state["step"] == 1:
        state["name"] = msg
        reply = "📧 Enter your email:"
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
        if msg.lower() in ["yes", "y"]:
            reply = "🔗 Send website link:"
            state["step"] = 6
        else:
            state["website_link"] = "No Website"
            create_odoo_lead(state)
            reply = "✅ Thank you! Our team will contact you."
            sessions.pop(user, None)

    elif state["step"] == 6:
        state["website_link"] = msg
        create_odoo_lead(state)
        reply = "✅ Thank you! Our team will contact you."
        sessions.pop(user, None)

    sessions[user] = state
    send_message(user, reply)

# =========================
# HEALTH CHECK
# =========================
@app.route("/ping")
def ping():
    return "alive"
