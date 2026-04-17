# ---------------- REFINED AI SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are 'Elite AI'. Be professional and high-end. 
You must collect exactly these three things:
1. The user's requirement/project.
2. Their official website URL (or if they don't have one yet).
3. Their budget.

Once (and ONLY once) you have all three, tell the user: 
"Thank you for contacting us! Your request is registered and our team will call you shortly."
Then, end your response with this exact hidden tag: [TRIGGER_ODOO]
"""

def create_odoo_lead(name, phone, history_log):
    # This extracts the data from the chat history
    # For a truly 'Elite' version, you could use a second AI call to summarize the log
    description = f"Full Chat History:\n{history_log}"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                os.environ.get("ODOO_DB"),
                int(os.environ.get("ODOO_USER_ID")),
                os.environ.get("ODOO_API_KEY"),
                "crm.lead",
                "create",
                [{
                    "name": f"AI Qualified Lead: {name}",
                    "contact_name": name,
                    "phone": phone,
                    "description": description
                }]
            ]
        },
        "id": 1
    }
    requests.post(os.environ.get("ODOO_URL"), json=payload)

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")
    response = MessagingResponse()

    if sender not in sessions:
        sessions[sender] = {"history": [], "name": "WhatsApp User"}
        response.message("👋 Welcome to Elite Services. What can we build for you?")
        return str(response)

    # 1. Get AI Reply
    ai_reply = get_ai_response(incoming_msg, sessions[sender]["history"])
    
    # 2. Check if AI added the trigger tag
    if "[TRIGGER_ODOO]" in ai_reply:
        # Clean the text so the user doesn't see the code tag
        clean_reply = ai_reply.replace("[TRIGGER_ODOO]", "").strip()
        response.message(clean_reply)
        
        # 3. PUSH TO ODOO
        chat_log = "\n".join([f"{m['role']}: {m['content']}" for m in sessions[sender]["history"]])
        create_odoo_lead(sessions[sender]["name"], sender, chat_log)
        
        # Clear session so they can start a new lead later
        sessions.pop(sender)
    else:
        response.message(ai_reply)
        # Save history for the next turn
        sessions[sender]["history"].append({"role": "user", "content": incoming_msg})
        sessions[sender]["history"].append({"role": "assistant", "content": ai_reply})

    return str(response)
