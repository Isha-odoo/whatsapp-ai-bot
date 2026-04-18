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
                        "name": f"WhatsApp Lead - {data.get('requirement') or 'New Inquiry'}",
                        "contact_name": name,
                        "phone": phone,
                        "description": f"""
Lead Generated via WhatsApp

Requirement: {data.get('requirement')}
Website: {data.get('website')}
Budget: {data.get('budget')}
"""
                    }]
                ]
            }
        }

        response = requests.post(ODOO_URL, json=payload, timeout=10)
        result = response.json()

        if "error" in result:
            print("Odoo ERROR:", result["error"])
        else:
            print("Lead Created Successfully:", result)

    except Exception as e:
        print("Odoo Exception:", e)

# =========================
# WHATSAPP WEBHOOK
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    try:
        incoming_msg = request.form.get("Body", "").strip()
        sender = request.form.get("From")

        print("Incoming:", incoming_msg)

        response = MessagingResponse()

        # Reset conversation
        if incoming_msg.lower() in ["hi", "hello", "restart"]:
            sessions.pop(sender, None)

        # Create session
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

        # Get session data
        data = sessions[sender]["data"]
        msg = incoming_msg.strip()
        msg_lower = msg.lower()

        # =========================
        # DATA CAPTURE (SAFE LOGIC)
        # =========================

        # Website detection
        if not data.get("website") and any(x in msg_lower for x in [".com", ".in", ".org", "www", "http"]):
            data["website"] = msg

        # Budget detection
        elif not data.get("budget") and any(char.isdigit() for char in msg):
            data["budget"] = msg

        # Requirement detection
        elif not data.get("requirement") and len(msg) > 4:
            data["requirement"] = msg

        # =========================
        # FLOW CONTROL
        # =========================

        if not data.get("requirement"):
            response.message("What service do you need?")
            return str(response)

        elif not data.get("website"):
            response.message("🌐 Please share your company website.")
            return str(response)

        elif not data.get("budget"):
            response.message("💰 What is your approximate budget?")
            return str(response)

        else:
            response.message("✅ Thank you! Our team will contact you shortly.")

            # Push to Odoo
            push_to_odoo(
                sessions[sender]["name"],
                sender,
                data
            )

            # Clear session
            sessions.pop(sender)

            return str(response)

    except Exception as e:
        print("MAIN ERROR:", e)
        return str(MessagingResponse().message("Server error"))

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
