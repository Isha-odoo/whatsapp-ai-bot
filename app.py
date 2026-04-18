import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)

# =========================
# ENV VARIABLES
# =========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")

# Odoo config
ODOO_URL = "https://edu-isha1.odoo.com/jsonrpc"
ODOO_DB = "edu-isha1"
ODOO_USER_ID = 2

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Session memory
sessions = {}

# =========================
# AI SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
You are a professional AI assistant.

Ask user step by step:
1. What service they need
2. Their company website
3. Their budget

Once all info is collected, reply:
"Thank you! Our team will contact you shortly."

Then add this at end: [TRIGGER_ODOO]
"""

# =========================
# ODOO PUSH FUNCTION
# =========================
def push_to_odoo(name, phone, chat_history):
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB, ODOO_USER_ID, ODOO_API_KEY,
                    "crm.lead", "create",
                    [{
                        "name": f"WhatsApp Lead - {name}",
                        "contact_name": name,
                        "phone": phone,
                        "description": chat_history
                    }]
                ]
            }
        }

        response = requests.post(ODOO_URL, json=payload, timeout=10)
        print("Odoo response:", response.text)

    except Exception as e:
        print("Odoo ERROR:", e)

# =========================
# AI FUNCTION
# =========================
def get_ai_reply(user_msg, history):
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_msg})

        completion = client.chat.completions.create(
            model="gpt-4.1-mini",  # safer model
            messages=messages
        )

        return completion.choices[0].message.content

    except Exception as e:
        print("AI ERROR:", e)
        return "Sorry, something went wrong. Please try again."

# =========================
# WHATSAPP WEBHOOK
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    try:
        incoming_msg = request.form.get("Body", "").strip()
        sender = request.form.get("From")

        print("Incoming:", incoming_msg)

        response = MessagingResponse()

        # Reset conversation
        if incoming_msg.lower() in ["hi", "hello", "restart"]:
            sessions.pop(sender, None)

        if sender not in sessions:
            sessions[sender] = {"history": [], "name": "User"}
            response.message("👋 Hi! What service do you need?")
            return str(response)

        # AI reply
        ai_reply = get_ai_reply(incoming_msg, sessions[sender]["history"])

        # Check trigger
        if "[TRIGGER_ODOO]" in ai_reply:
            final_msg = ai_reply.replace("[TRIGGER_ODOO]", "").strip()
            response.message(final_msg)

            # Prepare chat log
            chat_log = "\n".join(
                [f"{m['role']}: {m['content']}" for m in sessions[sender]["history"]]
            )

            push_to_odoo("WhatsApp User", sender, chat_log)

            sessions.pop(sender)

        else:
            response.message(ai_reply)

            sessions[sender]["history"].append(
                {"role": "user", "content": incoming_msg}
            )
            sessions[sender]["history"].append(
                {"role": "assistant", "content": ai_reply}
            )

        return str(response)

    except Exception as e:
        print("MAIN ERROR:", e)
        return str(MessagingResponse().message("Server error"))

# =========================
# HEALTH CHECK
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running 🚀"

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
