import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# =========================
# ENV VARIABLES
# =========================
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")

ODOO_URL = "https://edu-isha1.odoo.com/jsonrpc"
ODOO_DB = "edu-isha1"
ODOO_USER_ID = 2

# =========================
# SESSION STORAGE
# =========================
sessions = {}

# =========================
# PUSH TO ODOO
# =========================
def push_to_odoo(name, phone, data):
    try:
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
                        "name": f"WhatsApp Lead - {data['requirement']}",
                        "contact_name": name,
                        "phone": phone,
                        "description": f"""
Requirement: {data['requirement']}
Website: {data['website']}
Budget: {data['budget']}
"""
                    }]
                ]
            }
        }

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

    response = MessagingResponse()

    # Reset conversation
    if incoming_msg.lower() in ["hi", "hello", "restart"]:
        sessions.pop(sender, None)

    # Initialize session
    if sender not in sessions:
        sessions[sender] = {
            "name": "WhatsApp User",
            "data": {
                "requirement": None,
                "website": None,
                "budget": None
            }
        }
        response.message("👋 Hi! What service do you need?")
        return str(response)

    data = sessions[sender]["data"]
    msg_lower = incoming_msg.lower()

# =========================
# SMART DATA CAPTURE (FIXED)
# =========================

# Detect website
if not data["website"]:
    if any(domain in msg_lower for domain in [".com", ".in", ".org", "www", "http"]):
        data["website"] = incoming_msg.strip()

# Detect budget
if not data["budget"]:
    if any(char.isdigit() for char in incoming_msg):
        data["budget"] = incoming_msg.strip()

# Detect requirement
if not data["requirement"]:
    if len(incoming_msg.strip()) > 4:
        data["requirement"] = incoming_msg.strip()
        
    # =========================
    # CONTROL FLOW
    # =========================

    if not data["requirement"]:
        response.message("What service do you need?")
        return str(response)

    elif not data["website"]:
        response.message("Please share your company website.")
        return str(response)

    elif not data["budget"]:
        response.message("What is your approximate budget?")
        return str(response)

    else:
        # All data collected
        response.message("✅ Thank you! Our team will contact you shortly.")

        push_to_odoo(
            sessions[sender]["name"],
            sender,
            data
        )

        sessions.pop(sender)
        return str(response)

# =========================
# HEALTH CHECK
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running 🚀"

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
