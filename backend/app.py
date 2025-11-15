# backend/app.py
import os
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ethicamind")

app = Flask(__name__)
CORS(app)

# Read API key from env
API_KEY = os.getenv("ETHICAMIND_API_KEY")
if not API_KEY:
    log.warning("ETHICAMIND_API_KEY not set; using fallback responses only.")

# Try to import the preferred client
GENAI_CLIENT = None
GENAI_TYPE = None

def try_import_clients():
    global GENAI_CLIENT, GENAI_TYPE
    try:
        import google_genai as genai  # package 'google-genai'
        GENAI_CLIENT = genai
        GENAI_TYPE = "google_genai"
        log.info("google_genai SDK available.")
    except Exception as e1:
        log.info("google_genai not available: %s", e1)
        try:
            import google.generativeai as ga  # older package name
            GENAI_CLIENT = ga
            GENAI_TYPE = "google.generativeai"
            log.info("google.generativeai SDK available.")
        except Exception as e2:
            log.info("No supported Google GenAI SDK available: %s | %s", e1, e2)
            GENAI_CLIENT = None
            GENAI_TYPE = None

try_import_clients()

# If google_genai is present, configure it
if GENAI_CLIENT and GENAI_TYPE == "google_genai" and API_KEY:
    # google_genai usage
    try:
        GENAI_CLIENT.configure(api_key=API_KEY)
        log.info("Configured google_genai client.")
    except Exception as e:
        log.exception("Failed to configure google_genai: %s", e)

if GENAI_CLIENT and GENAI_TYPE == "google.generativeai" and API_KEY:
    try:
        GENAI_CLIENT.configure(api_key=API_KEY)
        log.info("Configured google.generativeai client.")
    except Exception as e:
        log.exception("Failed to configure google.generativeai: %s", e)


def send_to_model(message_text, timeout_s=10):
    """
    Try google_genai first, then google.generativeai; else fallback.
    Returns a string reply.
    """
    if not API_KEY:
        log.warning("No API key provided — using fallback response.")
        return "Sorry — I'm having trouble reaching the AI service; please try again later."

    if GENAI_CLIENT and GENAI_TYPE == "google_genai":
        try:
            # google-genai client usage (typical)
            resp = GENAI_CLIENT.chat.create(
                model="chat-bison-001",
                input=message_text,
                max_output_tokens=256
            )
            # The exact shape may vary; handle sensibly
            if hasattr(resp, "candidates") and len(resp.candidates) > 0:
                return resp.candidates[0].content
            if hasattr(resp, "output") and isinstance(resp.output, str):
                return resp.output
            # generic fallback
            return str(resp)
        except Exception as e:
            log.exception("GenAI (google_genai) call exception: %s", e)

    if GENAI_CLIENT and GENAI_TYPE == "google.generativeai":
        try:
            # older google.generativeai usage
            resp = GENAI_CLIENT.generate_text(model="chat-bison-001", prompt=message_text)
            # adjust to response shape
            if hasattr(resp, "text"):
                return resp.text
            return str(resp)
        except Exception as e:
            log.exception("GenAI (google.generativeai) call exception: %s", e)

    # If all GenAI calls fail, return fallback message
    log.warning("Exhausted GenAI clients; using fallback.")
    return "Sorry — I'm having trouble reaching the AI service; please try again later."


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    msg = data.get("message", "").strip()
    if not msg:
        return jsonify({"error": "no message provided"}), 400

    log.info("Incoming message (len=%d): %s", len(msg), msg[:120])
    reply = None
    try:
        reply = send_to_model(msg)
    except Exception as e:
        log.exception("Failed to get model reply: %s", e)
        reply = "Sorry — I'm having trouble reaching the AI service; please try again later."

    return jsonify({"type": "chat", "message": reply})

# Root route to get a simple health check page
@app.route("/")
def index():
    return "EthicaMind backend is running."

if __name__ == "__main__":
    # Local dev: enable debug only locally
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
