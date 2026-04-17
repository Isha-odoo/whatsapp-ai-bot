from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.get("/")
def welcomepage():
    return {"message": "instance is active"}

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    msg = request.form.get("Body")

    reply = "Hi 👋 I am your AI assistant. You said: " + msg

    response = MessagingResponse()
    response.message(reply)

    return str(response)

if __name__ == "__main__":
    app.run()
