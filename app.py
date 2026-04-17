from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests

app = Flask(__name__)

sessions = {}

def create_odoo_lead(name, phone, requirement, budget):
    url = "https://edu-isha1.odoo.com/jsonrpc"

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                "edu-isha1",
                2,
                "385913b70e3508d9aa7bdeec0b29ed89c1b2389d",
                "crm.lead",
                "create",
                [{
                    "name": f"WhatsApp Lead - {name}",
                    "contact_name": name,
                    "phone": phone,
                    "description": f"Requirement: {requirement}\nBudget: {budget}"
                }]
            ]
        },
        "id": 1
    }

    r = requests.post(url, json=payload)
    print("ODOO RESPONSE:", r.text)
    return r.json()


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    msg = request.form.get("Body").strip()
    sender = request.form.get("From")

    if sender not in sessions:
        sessions[sender] = {
            "name": None,
            "requirement": None,
            "budget": None
        }

    session = sessions[sender]
    response = MessagingResponse()

    # ---------------- AI LOGIC ----------------

    if not session["name"]:
        session["name"] = msg
        response.message("👍 Nice! What service are you looking for?")
        return str(response)

    if not session["requirement"]:
        session["requirement"] = msg
        response.message("💰 What is your budget?")
        return str(response)

    if not session["budget"]:
        session["budget"] = msg

        # CREATE LEAD
        result = create_odoo_lead(
            session["name"],
            sender,
            session["requirement"],
            session["budget"]
        )

        response.message("✅ Thanks! Your request is registered. Our team will contact you soon.")

        sessions.pop(sender)
        return str(response)

    return str(response)


@app.get("/")
def home():
    return {"status": "running"}
