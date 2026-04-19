from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    print("🔥 WhatsApp HIT")

    # Get incoming message
    incoming_msg = request.values.get("Body", "").strip().lower()
    print("Incoming:", incoming_msg)

    # Simple logic bot (NO AI)
    if incoming_msg in ["hi", "hello", "hey"]:
        reply = "👋 Hello! I am your WhatsApp bot. Ask me anything simple."
    elif "price" in incoming_msg:
        reply = "💰 Please tell me which product you want pricing for."
    elif "help" in incoming_msg:
        reply = "🛠 I can respond to greetings, price, and help messages."
    else:
        reply = f"🤖 You said: {incoming_msg}"

    # Twilio response
    resp = MessagingResponse()
    resp.message(reply)

    return str(resp)


@app.route("/")
def home():
    return "WhatsApp Bot is Running ✅"


if __name__ == "__main__":
    app.run(debug=True)
