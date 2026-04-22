from flask import Flask, request
import requests
import os
from supabase import create_client

app = Flask(__name__)

# =========================
# META CONFIG
# =========================
VERIFY_TOKEN = "abc123"
WHATSAPP_TOKEN = "YOUR_META_ACCESS_TOKEN"
PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID"

# =========================
# SUPABASE CONFIG
# =========================
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# SESSION STORAGE
# =========================
sessions = {}

# =========================
# GET CLIENT FROM DB
# =========================
def get_client(phone_number_id):
    res = supabase.table("clients").select("*").eq("phone_number_id", phone_number_id).execute()
    return res.data[0] if res.data else None

# =========================
# SEND WHATSAPP MESSAGE
# =========================
def send_message(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }

    res = requests.post(url, headers=headers, json=data)
    print("Send:", res.text)

# =========================
# CREATE ODOO LEAD
# =========================
def create_odoo_lead(client, data):
    try:
        # AUTH
        auth_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [client["db"], client["username"], client["api_key"]]
            },
            "id": 1
        }

        auth = requests.post(f"{client['odoo_url']}/jsonrpc", json=auth_payload).json()
        uid = auth.get("result")

        if not uid:
            print("❌ Odoo Auth Failed")
            return

        # CREATE LEAD
        lead_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    client["db"],
                    uid,
                    client["api_key"],
                    "crm.lead",
                    "create",
                    [{
                        "name": f"WhatsApp Lead - {data.get('name')}",
                        "contact_name": data.get("name"),
                        "phone": data.get("phone"),
                        "email_from": data.get("email"),
                        "description": f"""
Service: {data.get('service')}
Budget: {data.get('budget')}
Website: {data.get('website')}
                        """
                    }]
                ]
            },
            "id": 2
        }

        res = requests.post(f"{client['odoo_url']}/jsonrpc", json=lead_payload)
        print("✅ Lead Created:", res.text)

    except Exception as e:
        print("❌ Odoo Error:", e)

# =========================
# WEBHOOK VERIFY (GET)
# =========================
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    return "Invalid token", 403

# =========================
# WEBHOOK RECEIVE (POST)
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "OK", 200

        # 🔥 MULTI CLIENT IDENTIFIER
        phone_number_id = value["metadata"]["phone_number_id"]

        # 👤 USER
        user = value["messages"][0]["from"]
        msg = value["messages"][0]["text"]["body"]

        print("CLIENT:", phone_number_id)
        print("USER:", user, "MSG:", msg)

        # 🔥 GET CLIENT DATA
        client = get_client(phone_number_id)

        if not client:
            print("❌ Client not found")
            return "OK", 200

        state = sessions.get(user, {"step": 0})

        # ================= BOT FLOW =================

        if state["step"] == 0:
            reply = "👋 Hi! What is your name?"
            state["step"] = 1

        elif state["step"] == 1:
            state["name"] = msg
            reply = "📧 Enter email:"
            state["step"] = 2

        elif state["step"] == 2:
            state["email"] = msg
            reply = "💼 What service do you need?"
            state["step"] = 3

        elif state["step"] == 3:
            state["service"] = msg
            reply = "💰 Budget?"
            state["step"] = 4

        elif state["step"] == 4:
            state["budget"] = msg
            reply = "🌐 Website? (yes/no)"
            state["step"] = 5

        elif state["step"] == 5:
            if msg.lower() == "yes":
                reply = "Send website link:"
                state["step"] = 6
            else:
                state["website"] = "No"
                state["phone"] = user

                create_odoo_lead(client, state)
                reply = "✅ Thank you! We’ll contact you."
                sessions.pop(user)

        elif state["step"] == 6:
            state["website"] = msg
            state["phone"] = user

            create_odoo_lead(client, state)
            reply = "✅ Thank you! We’ll contact you."
            sessions.pop(user)

        sessions[user] = state

        send_message(user, reply)

    except Exception as e:
        print("❌ Webhook Error:", e)

    return "OK", 200

# =========================
# HEALTH
# =========================
@app.route("/ping")
def ping():
    return "alive"

if __name__ == "__main__":
    app.run(debug=True)
