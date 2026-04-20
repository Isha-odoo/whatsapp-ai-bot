from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running ✅"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    print("🔥 TEST HIT /whatsapp")

    incoming_msg = request.values.get("Body", "")
    print("Incoming:", incoming_msg)

    resp = MessagingResponse()
    resp.message("✅ WORKING NOW")

    return str(resp)

if __name__ == "__main__":
    app.run()
