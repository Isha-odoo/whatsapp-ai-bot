import os
import requests
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)

# =========================
# CONFIG
# =========================
ODOO_URL = "https://edu-isha1.odoo.com/jsonrpc"
ODOO_DB = "edu-isha1"
ODOO_USER_ID = 2
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

sessions = {}

# =========================
# AI EXTRACTION
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

Return ONLY JSON:
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
    phone = phone.replace("whatsapp:", "")

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
    print("Odoo Response:", res.text)

# =========================
# WHATSAPP WEBHOOK
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")

    response = MessagingResponse()

    # Reset
    if incoming_msg.lower() in ["hi", "hello", "restart"]:
        sessions.pop(sender, None)

    # Create session
    if sender not in sessions:
        sessions[sender] = {
            "name": None,
            "email": None,
            "requirement": None,
            "website": None,
            "budget": None
        }
        response.message("👋 Hi! What service are you looking for?")
        return str(response)

    lead = sessions[sender]

    # =========================
    # AI EXTRACTION
    # =========================
    ai_data = extract_data(incoming_msg)

    for key in lead:
        if not lead[key] and ai_data.get(key):
            lead[key] = ai_data[key]

    # =========================
    # FLOW CONTROL
    # =========================
    if not lead["requirement"]:
        response.message("What service do you need?")
        return str(response)

    elif not lead["name"]:
        response.message("May I know your name?")
        return str(response)

    elif not lead["email"]:
        response.message("Please share your email address.")
        return str(response)

    elif not lead["website"]:
        response.message("🌐 Please share your company website.")
        return str(response)

    elif not lead["budget"]:
        response.message("💰 What is your approximate budget?")
        return str(response)

    else:
        response.message("✅ Thank you! Our team will contact you shortly.")
        push_to_odoo(sender, lead)
        sessions.pop(sender)
        return str(response)

# =========================
# HEALTH CHECK
# =========================
@app.route("/")
def home():
    return "Bot is running 🚀"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
