import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)
sessions = {}

# --- AI QUALIFICATION PROMPT ---
AI_SYSTEM_PROMPT = """
You are a lead qualification assistant for Elite Services. 
Your goal is to find out:
1. What the client needs (Project scope).
2. Their budget (Must be over $1000).
3. Their timeline.
If the lead is qualified, summarize their details. If not, be polite but don't promise a call.
"""

def call_ai_agent(user_msg, chat_history):
    # This is where you connect to OpenAI or Gemini
    # For now, we simulate an AI response that decides if the lead is "QUALIFIED"
    # Example logic: AI returns a JSON-like summary
    return "That sounds like a great project! To give you an accurate quote, what is your rough budget for this?"

def create_odoo_lead(data, phone):
    # Logic to push to Odoo (same as before)
    pass

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")
    response = MessagingResponse()

    if sender not in sessions:
        sessions[sender] = {"history": [], "qualified": False}
        response.message("👋 Hello! I'm the Elite AI. How can I help you grow your business today?")
        return str(response)

    # 1. AI Processes the message
    chat_history = sessions[sender]["history"]
    ai_reply = call_ai_agent(msg, chat_history)
    
    # 2. Update History
    sessions[sender]["history"].append({"user": msg, "bot": ai_reply})

    # 3. Qualification Logic
    # If the AI detects all info is present, it marks as qualified
    if "BUDGET:" in ai_reply and "SCOPE:" in ai_reply:
        create_odoo_lead(ai_reply, sender)
        response.message("✅ AI Analysis Complete: You've been qualified! An expert will call you.")
        sessions.pop(sender)
    else:
        response.message(ai_reply)

    return str(response)
