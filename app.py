import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

app = Flask(__name__)
sessions = {}

# Initialize OpenAI Client
# Set OPENAI_API_KEY in your Render environment variables
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------- AI QUALIFICATION ENGINE ----------------
SYSTEM_PROMPT = """
You are 'Elite AI', a high-end sales qualifier. Your goal is to chat naturally.
Qualify the lead by finding:
1. Name and Industry.
2. Specific Pain Point/Requirement.
3. Budget (Must be > $2,000 for 'High-End' status).

If the lead provides all info, end your response with the tag: [QUALIFIED]
"""

def get_ai_response(user_input, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    return response.choices[0].message.content

# ---------------------------------------------------------

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")
    response = MessagingResponse()

    if sender not in sessions:
        sessions[sender] = {"history": []}
        ai_greeting = "👋 Welcome to Elite Services. I'm your AI consultant. How can we help you today?"
        response.message(ai_greeting)
        return str(response)

    # Get AI's take on the conversation
    ai_reply = get_ai_response(incoming_msg, sessions[sender]["history"])
    
    # Store history
    sessions[sender]["history"].append({"role": "user", "content": incoming_msg})
    sessions[sender]["history"].append({"role": "assistant", "content": ai_reply})

    # Check for Qualification Tag
    if "[QUALIFIED]" in ai_reply:
        # Clean the tag for the user
        final_reply = ai_reply.replace("[QUALIFIED]", "")
        response.message(f"{final_reply}\n\n✅ *Status: Qualified. Sending to Odoo CRM...*")
        
        # Here: Trigger your existing Odoo create_lead function
        # create_odoo_lead(sessions[sender])
        
        sessions.pop(sender) # Reset session
    else:
        response.message(ai_reply)

    return str(response)

@app.route("/")
def home():
    return {"status": "AI Qualification Bot Online"}, 200
