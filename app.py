import os
import requests
import json
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

# =========================
# CONFIG
# =========================
ODOO_URL = "https://edu-isha1.odoo.com/jsonrpc"
ODOO_DB = "edu-isha1"
ODOO_USER_ID = 2
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")

PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

sessions = {}

# =========================
# SEND WHATSAPP MESSAGE (META API)
# =========================
def send_message(to, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    requests.post(url, headers=headers, json=payload)

# =========================
# AI DATA EXTRACTION
# =========================
def extract_data(message):
    prompt = f"""
Extract:
- name
- email
- requirement
- website
- budget

Message: "{message}"

Return JSON:
{{
"name": "",
"email": "",
"requirement": "",
"website": "",
"budget": ""
}}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return json.loads(res.choices[0].message.content)
    except:
        return {}

# =========================
# PUSH TO ODOO
# =========================
def push_to_odoo(phone, data):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                ODOO_DB,
                ODOO_USER_ID,
                ODOO_API_KEY,
                "crm.lead",
                "create",
                [{
                    "name": f"WhatsApp Lead - {data.get('requirement') or 'New Inquiry'}",
                    "contact_name": data.get("name"),
                    "email_from": data.get("email"),
                    "phone": phone,
                    "description": str(data)
                }]
            ]
        }
    }

    res = requests.post(ODOO_URL, json=payload)
    print("Odoo:", res.text)

# =========================
# WEBHOOK VERIFY
# =========================
@app.route("/webhook", methods=["GET"])
def verify():
    VERIFY_TOKEN = "myverify123"

    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error"

# =========================
# MAIN WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]
        text = message["text"]["body"]

        if sender not in sessions:
            sessions[sender] = {
                "name": None,
                "email": None,
                "requirement": None,
                "website": None,
                "budget": None
            }

        lead = sessions[sender]

        # AI extraction
        ai_data = extract_data(text)

        for key in lead:
            if not lead[key] and ai_data.get(key):
                lead[key] = ai_data[key]

        # FLOW
        if not lead["requirement"]:
            send_message(sender, "What service do you need?")
        elif not lead["name"]:
            send_message(sender, "May I know your name?")
        elif not lead["email"]:
            send_message(sender, "Please share your email")
        elif not lead["website"]:
            send_message(sender, "Share your website")
        elif not lead["budget"]:
            send_message(sender, "Your budget?")
        else:
            send_message(sender, "✅ Thank you! Our team will contact you.")
            push_to_odoo(sender, lead)
            sessions.pop(sender)

    except Exception as e:
        print("Error:", e)

    return "ok"

@app.route("/")
def home():
    return "Running"
