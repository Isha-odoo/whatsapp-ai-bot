from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

# ✅ FIRST define app
app = Flask(__name__)

# ✅ THEN routes
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    print("🔥 HIT")

    msg = request.form.get("Body")
    print("Incoming:", msg)

    resp = MessagingResponse()
    resp.message("Bot working ✅")

    return str(resp)

@app.route("/")
def home():
    return "OK"
