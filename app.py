import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)

# Securely load credentials from Render Environment Variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ODOO_URL = "https://edu-isha1.odoo.com/jsonrpc"
ODOO_DB = "edu-isha1"
ODOO_USER_ID = 2  # As confirmed from your settings URL
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")

# Initialize OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Session storage (In-memory)
sessions = {}

# --- AI CONFIGURATION ---
SYSTEM_PROMPT = """
You are the 'Elite AI Consultant'. Your tone is premium, professional, and concise.
Your objective is to qualify a lead by collecting:
1. The specific service or project requirement.
2. Their official company website URL.
3. Their estimated project budget.

Once (and ONLY once) you have all three pieces of information, respond with:
"Thank you for contacting Elite Services! Your project details are registered, and our senior consultant will call you shortly."
Then, append the hidden tag [TRIGGER_ODOO] at the very end of your message.
"""

# --- ODOO INTEGRATION ---
def push_to_odoo(name, phone, chat_history):
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
                    "name": f"AI Qualified: {name}",
                    "contact_name": name,
                    "phone": phone,
                    "description": f"QUALIFIED VIA WHATSAPP AI\n\nFull Chat Log:\n{chat_history}"
                }]
            ]
        },
        "id": 1
    }
    try:
        response = requests.post(ODOO_URL, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Odoo Error: {e}")
        return None

# --- AI BRAIN ---
def get_ai_reply(user_msg, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_msg})
    
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7
    )
    return completion.choices[0].message.content

# --- WHATSAPP WEBHOOK ---
@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "").strip()
    sender_phone = request.form.get("From")
    response = MessagingResponse()

    # Reset command
    if incoming_msg.lower() in ["hi", "hello", "restart", "menu"]:
        sessions.pop(sender_phone, None)

    if sender_phone not in sessions:
        sessions[sender_phone] = {"history": [], "name": "WhatsApp Client"}
        greeting = "👋 Welcome to Elite Services. I'm your AI consultant. What high-end project can we help you with today?"
        response.message(greeting)
        return str(response)

    # 1. Process with AI
    ai_response = get_ai_reply(incoming_msg, sessions[sender_phone]["history"])

    # 2. Check for the Odoo Trigger Tag
    if "[TRIGGER_ODOO]" in ai_response:
        final_msg = ai_response.replace("[TRIGGER_ODOO]", "").strip()
        response.message(final_msg)
        
        # Build Chat Log
        full_log = "\n".join([f"{m['role']}: {m['content']}" for m in sessions[sender_phone]["history"]])
        full_log += f"\nUser: {incoming_msg}\nAI: {final_msg}"
        
        # 3. Create Lead in Odoo
        push_to_odoo(sessions[sender_phone]["name"], sender_phone, full_log)
        
        # Clear session after successful qualification
        sessions.pop(sender_phone)
    else:
        # Standard AI flow
        response.message(ai_response)
        # Update history
        sessions[sender_phone]["history"].append({"role": "user", "content": incoming_msg})
        sessions[sender_phone]["history"].append({"role": "assistant", "content": ai_response})

    return str(response)

@app.route("/", methods=["GET"])
def health_check():
    return {"status": "Elite AI Bot is Active", "odoo_instance": ODOO_DB}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
