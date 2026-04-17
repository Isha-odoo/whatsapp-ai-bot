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
                2,  # user id
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

    requests.post(url, json=payload)


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    msg = request.form.get("Body")
    sender = request.form.get("From")

    if sender not in sessions:
        sessions[sender] = {"step": 1}

    session = sessions[sender]

    response = MessagingResponse()

    # STEP FLOW
    if session["step"] == 1:
        session["name"] = msg
        session["step"] = 2
        response.message("Great 👍 What is your requirement?")

    elif session["step"] == 2:
        session["requirement"] = msg
        session["step"] = 3
        response.message("What is your budget?")

    elif session["step"] == 3:
        session["budget"] = msg
        session["step"] = 4

        # CREATE ODOO LEAD
        create_odoo_lead(
            session["name"],
            sender,
            session["requirement"],
            session["budget"]
        )

        response.message("✅ Thanks! Your request is registered. Our team will contact you.")

        sessions.pop(sender)

    return str(response)


@app.get("/")
def home():
    return {"status": "running"}
