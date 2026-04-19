@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From")

    print("Incoming:", incoming_msg)

    resp = MessagingResponse()

    # Reset
    if incoming_msg.lower() == "restart":
        sessions.pop(sender, None)

    # New user
    if sender not in sessions:
        sessions[sender] = {
            "requirement": None,
            "contact_name": None,
            "email": None,
            "website": None,
            "budget": None
        }
        resp.message("👋 Hi! What service do you need?")
        return str(resp)

    lead = sessions[sender]

    # Ignore greetings AFTER session created
    if incoming_msg.lower() in ["hi", "hello", "hey"]:
        resp.message("What service do you need?")
        return str(resp)

    # Requirement
    if not lead["requirement"]:
        lead["requirement"] = incoming_msg
        resp.message("May I know your name?")
        return str(resp)

    # Name
    if not lead["contact_name"]:
        lead["contact_name"] = incoming_msg.title()
        resp.message("Please share your email address.")
        return str(resp)

    # Email
    if not lead["email"]:
        if "@" not in incoming_msg:
            resp.message("❌ Please enter a valid email (example: name@gmail.com)")
            return str(resp)

        lead["email"] = incoming_msg
        resp.message("🌐 Please share your company website.")
        return str(resp)

    # Website
    if not lead["website"]:
        if ".com" not in incoming_msg:
            resp.message("❌ Please enter a valid website (example: abc.com)")
            return str(resp)

        lead["website"] = incoming_msg
        resp.message("💰 What is your approximate budget?")
        return str(resp)

    # Budget
    if not lead["budget"]:
        lead["budget"] = incoming_msg

        resp.message("✅ Thank you! Our team will contact you shortly.")

        push_to_odoo(sender, lead)
        sessions.pop(sender)

        return str(resp)

    resp.message("Something went wrong. Type restart.")
    return str(resp)
