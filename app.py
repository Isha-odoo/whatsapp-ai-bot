import os
import requests
import re
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
# HELPER FUNCTIONS
# =========================

def extract_email(msg):
    match = re.search(r'[\w\.-]+@[\w\.-]+', msg)
    return match.group(0) if match else None

def extract_website(msg):
    if "http" in msg or "www" in msg or ".com" in msg:
        return msg.strip()
    return None

def extract_budget(msg):
    if any(x in msg.lower() for x in ["k", "₹", "rs", "rupee"]):
        return msg.strip()
    return None

def extract_name(msg):
    if "i am" in msg.lower():
        return msg.lower().split("am")[-1].split(".")[0].strip().title()
    if msg.isalpha() and len(msg) > 2:
        return msg.title()
    return None

def extract_requirement(msg):
    msg_lower = msg.lower()
    if "website" in msg_lower:
        return "Website Development"
    if "seo" in msg_lower:
        return "SEO Service"
    if "app" in msg_lower:
        return "App Development"
    return None

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
                    "description": f"""
Name: {data.get('name')}
Email: {data.get('email')}
Requirement: {data.get('requirement')}
Website: {data.get('website')}
Budget: {data.get('budget')}
"""
                }]
            ]
        }
    }

    requests.post(ODOO_URL, json=payload)

# =========================
# WHATSAPP BOT
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")

    response = MessagingResponse()

    # Restart only if user says restart
    if msg.lower() == "restart":
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
    # SMART DATA CAPTURE
    # =========================
    if not lead["email"]:
        email = extract_email(msg)
        if email:
            lead["email"] = email

    if not lead["website"]:
        website = extract_website(msg)
        if website:
            lead["website"] = website

    if not lead["budget"]:
        budget = extract_budget(msg)
        if budget:
            lead["budget"] = budget

    if not lead["name"]:
        name = extract_name(msg)
        if name:
            lead["name"] = name

    if not lead["requirement"]:
        requirement = extract_requirement(msg)
        if requirement:
            lead["requirement"] = requirement

    print("SESSION:", lead)

    # =========================
    # CHECK COMPLETE
    # =========================
    if all(lead.values()):
        response.message("✅ Thank you! Our team will contact you shortly.")
        push_to_odoo(sender, lead)
        sessions.pop(sender)
        return str(response)

    # =========================
    # ASK NEXT QUESTION
    # =========================
    if not lead["requirement"]:
        response.message("What service do you need?")
    elif not lead["name"]:
        response.message("May I know your name?")
    elif not lead["email"]:
        response.message("Please share your email address.")
    elif not lead["website"]:
        response.message("🌐 Please share your company website.")
    elif not lead["budget"]:
        response.message("💰 What is your approximate budget?")

    return str(response)

# =========================
# HEALTH
# =========================
@app.route("/")
def home():
    return "Bot running 🚀"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
