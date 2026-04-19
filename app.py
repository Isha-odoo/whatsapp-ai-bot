from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    print("🔥 HIT")

    incoming_msg = request.form.get("Body", "")
    print("Incoming:", incoming_msg)

    resp = MessagingResponse()
    resp.message("Bot working ✅")

    return str(resp)

@app.route("/")
def home():
    return "OK"
