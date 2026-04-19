import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# =========================
# CONFIG
# =========================
ODOO_URL = "https://edu-isha1.odoo.com/jsonrpc"
ODOO_DB = "edu-isha1"
ODOO_USER_ID = 2
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")

sessions = {}

# =========================
# PUSH TO ODOO
# =========================
def push_to_odoo(name, phone, data):
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
                    "contact_name": data.get("contact_name"),
                    "email_from": data.get("email"),
                    "phone": phone,
                    "description": f"""
Lead Generated via WhatsApp

Name: {data.get('contact_name')}
Email: {data.get('email')}
Requirement: {data.get('requirement')}
Website: {data.get('website')}
Budget: {data.get('budget')}
"""
                }]
            ]
        }
    }

    try:
        response = requests.post(ODOO_URL, json=payload, timeout=10)
        print("Odoo Response:", response.text)
    except Exception as e:
        print("Odoo Error:", e)

# =========================
# WHATSAPP WEBHOOK
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")

    print("Incoming:", incoming_msg)

    response = MessagingResponse()

    # Reset ONLY on restart
    if incoming_msg.lower() == "restart":
        sessions.pop(sender, None)

    # Initialize session
    if sender not in sessions:
        sessions[sender] = {
            "data": {
                "requirement": None,
                "contact_name": None,
                "email": None,
                "website": None,
                "budget": None
            }
        }
        response.message("👋 Hi! What service do you need?")
        return str(response)

    data = sessions[sender]["data"]

    # =========================
    # STEP-BY-STEP CAPTURE
    # =========================

    if not data["requirement"]:
        data["requirement"] = incoming_msg
        response.message("May I know your name?")
        return str(response)

    elif not data["contact_name"]:
        data["contact_name"] = incoming_msg
        response.message("Please share your email address.")
        return str(response)

    elif not data["email"]:
        data["email"] = incoming_msg
        response.message("🌐 Please share your company website.")
        return str(response)

    elif not data["website"]:
        data["website"] = incoming_msg
        response.message("💰 What is your approximate budget?")
        return str(response)

    elif not data["budget"]:
        data["budget"] = incoming_msg

        # All data collected
        response.message("✅ Thank you! Our team will contact you shortly.")

        push_to_odoo(
            data["contact_name"],
            sender,
            data
        )

        sessions.pop(sender)
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
