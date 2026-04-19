from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    print("🔥 HIT")

    incoming_msg = request.form.get("Body", "")
    print("Incoming:", incoming_msg)

    response = MessagingResponse()
    message = response.message()
    message.body("Bot working ✅")

    # 🔥 IMPORTANT: exact Twilio XML response
    return Response(str(response), content_type="application/xml")

@app.route("/")
def home():
    return "OK"
