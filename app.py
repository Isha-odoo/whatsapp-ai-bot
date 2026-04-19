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
# VALIDATION FUNCTIONS
# =========================
def is_valid_email(text):
    return "@" in text and "." in text

def is_valid_website(text):
    return any(x in text.lower() for x in [".com", ".in", ".org", "www", "http"])

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
        res = requests.post(ODOO_URL, json=payload, timeout=10)
        print("Odoo Response:", res.text)
    except Exception as e:
        print("Odoo Error:", e)

# =========================
# WHATSAPP BOT
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")

    print("Incoming:", incoming_msg)

    response = MessagingResponse()

    # Reset session
    if incoming_msg.lower() == "restart":
        sessions.pop(sender, None)

    # Initialize session
    if sender not in sessions:
        sessions[sender] = {
            "requirement": None,
            "contact_name": None,
            "email": None,
            "website": None,
            "budget": None
        }
        response.message("👋 Hi! What service do you need?")
        return str(response)

    lead = sessions[sender]

    # Ignore greetings
    if incoming_msg.lower() in ["hi", "hello", "hey"]:
        response.message("What service do you need?")
        return str(response)

    # =========================
    # FLOW
    # =========================

    # Requirement
    if not lead["requirement"]:
        lead["requirement"] = incoming_msg
        response.message("May I know your name?")
        return str(response)

    # Name
    elif not lead["contact_name"]:
        lead["contact_name"] = incoming_msg.title()
        response.message("Please share your email address.")
        return str(response)

    # Email (VALIDATION)
    elif not lead["email"]:
        if not is_valid_email(incoming_msg):
            response.message("❌ Please enter a valid email (example: name@gmail.com)")
            return str(response)

        lead["email"] = incoming_msg
        response.message("🌐 Please share your company website.")
        return str(response)

    # Website (VALIDATION)
    elif not lead["website"]:
        if not is_valid_website(incoming_msg):
            response.message("❌ Please enter a valid website (example: abc.com)")
            return str(response)

        lead["website"] = incoming_msg
        response.message("💰 What is your approximate budget?")
        return str(response)

    # Budget
    elif not lead["budget"]:
        lead["budget"] = incoming_msg

        response.message("✅ Thank you! Our team will contact you shortly.")

        push_to_odoo(sender, lead)

        sessions.pop(sender)
        return str(response)

    return str(response)

# =========================
# HEALTH
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
