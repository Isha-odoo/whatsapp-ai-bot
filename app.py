from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# =========================
# SIMPLE IN-MEMORY SESSION
# =========================
sessions = {}

# =========================
# WHATSAPP BOT
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    print("🔥 WHATSAPP HIT")

    user = request.values.get("From")
    msg = request.values.get("Body", "").strip()

    print(f"{user}: {msg}")

    # Get or create session
    state = sessions.get(user, {"step": 0})

    reply = ""

    # =========================
    # STEP FLOW
    # =========================

    if state["step"] == 0:
        reply = "👋 Hi! Welcome to our service.\nWhat is your name?"
        state["step"] = 1

    elif state["step"] == 1:
        state["name"] = msg
        reply = f"Nice to meet you {msg}! 😊\nWhat service do you need?"
        state["step"] = 2

    elif state["step"] == 2:
        state["service"] = msg
        reply = "💰 What is your budget?"
        state["step"] = 3

    elif state["step"] == 3:
        state["budget"] = msg
        reply = "🌐 Do you have a website? (yes/no)"
        state["step"] = 4

    elif state["step"] == 4:
        state["website"] = msg

        # =========================
        # FINAL LEAD DATA
        # =========================
        print("🔥 FINAL LEAD DATA:")
        print(state)

        reply = "✅ Thank you! Our team will contact you soon."

        # 👉 HERE you will later send data to Odoo

        # Reset session
        sessions.pop(user, None)

    # Save session
    sessions[user] = state

    # Twilio response
    resp = MessagingResponse()
    resp.message(reply)

    return str(resp)


# =========================
# HEALTH CHECK
# =========================
@app.route("/")
def home():
    return "WhatsApp Bot is LIVE ✅"


@app.route("/ping")
def ping():
    return "alive"


# =========================
# RUN LOCAL
# =========================
if __name__ == "__main__":
    app.run(debug=True)
