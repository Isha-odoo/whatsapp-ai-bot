from flask import Flask, request
import requests
import os
from supabase import create_client

app = Flask(__name__)

# =========================
# META CONFIG (USE ENV)
# =========================
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "abc123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# =========================
# SUPABASE CONFIG
# =========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None

# SAFE SUPABASE INIT
if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL.startswith("https://"):
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connected")
    except Exception as e:
        print("❌ Supabase init error:", e)
else:
    print("⚠️ Supabase not configured properly (check env variables)")


# =========================
# SESSION STORAGE (RAM)
# =========================
sessions = {}

# =========================
# GET CLIENT FROM DB
# =========================
def get_client(phone_number_id):
    res = supabase.table("clients") \
        .select("*") \
        .eq("phone_number_id", str(phone_number_id)) \
        .execute()

    return res.data[0] if res.data else None

    try:
        res = supabase.table("clients").select("*").eq("phone_number_id", phone_number_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print("❌ Supabase query error:", e)
        return None


# =========================
# SEND WHATSAPP MESSAGE
# =========================
def send_message(to, message):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("❌ WhatsApp config missing")
        return

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
    print("📤 WhatsApp:", res.status_code, res.text)


# =========================
# CREATE ODOO LEAD
# =========================
def create_odoo_lead(client, data):
    try:
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
            print("❌ Odoo login failed")
            return

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
# VERIFY WEBHOOK
# =========================
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    return "Invalid token", 403


# =========================
# RECEIVE MESSAGE
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        value = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})

        if "messages" not in value:
            return "OK", 200

        phone_number_id = value["metadata"]["phone_number_id"]
        user = value["messages"][0]["from"]

        msg_obj = value["messages"][0]
        msg = msg_obj.get("text", {}).get("body", "")

        print("📩 USER:", user, "MSG:", msg)

        client = get_client(user)
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
                sessions.pop(user, None)

        elif state["step"] == 6:
            state["website"] = msg
            state["phone"] = user

            create_odoo_lead(client, state)
            reply = "✅ Thank you! We’ll contact you."
            sessions.pop(user, None)

        sessions[user] = state

        send_message(user, reply)

    except Exception as e:
        print("❌ Webhook Error:", e)

    return "OK", 200


# =========================
# HEALTH CHECK
# =========================
@app.route("/ping")
def ping():
    return "alive"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
