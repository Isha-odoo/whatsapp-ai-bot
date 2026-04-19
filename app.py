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
Extract the following fields from the message:

- name
- email
- requirement
- website
- budget

Rules:
- If not found, return null
- Return ONLY valid JSON
- No extra text

Message: "{message}"

Output:
{{
"name": null,
"email": null,
"requirement": null,
"website": null,
"budget": null
}}
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print("AI ERROR:", e)
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

    try:
        res = requests.post(ODOO_URL, json=payload)
        print("Odoo Response:", res.text)
    except Exception as e:
        print("Odoo Error:", e)

# =========================
# WHATSAPP WEBHOOK
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")

    response = MessagingResponse()

    # ONLY restart if explicitly asked
    if incoming_msg.lower() == "restart":
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

    print("AI DATA:", ai_data)

    for key in lead:
        value = ai_data.get(key)
        if value and str(value).strip().lower() not in ["", "null", "none"]:
            lead[key] = str(value).strip()

    print("SESSION:", lead)

    # =========================
    # FULL DATA CHECK
    # =========================
    if all([
        lead.get("requirement"),
        lead.get("name"),
        lead.get("email"),
        lead.get("website"),
        lead.get("budget")
    ]):
        response.message("✅ Thank you! Our team will contact you shortly.")
        push_to_odoo(sender, lead)
        sessions.pop(sender)
        return str(response)

    # =========================
    # FLOW CONTROL
    # =========================
    if not lead.get("requirement"):
        response.message("What service do you need?")
        return str(response)

    elif not lead.get("name"):
        response.message("May I know your name?")
        return str(response)

    elif not lead.get("email"):
        response.message("Please share your email address.")
        return str(response)

    elif not lead.get("website"):
        response.message("🌐 Please share your company website.")
        return str(response)

    elif not lead.get("budget"):
        response.message("💰 What is your approximate budget?")
        return str(response)

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
