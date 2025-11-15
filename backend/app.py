# app.py
import os
import time
import logging
import traceback
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load local .env (only used in local dev)
load_dotenv()

# Logging
logger = logging.getLogger("ethicamind")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Config
API_KEY = os.environ.get("ETHICAMIND_API_KEY")
USE_MOCK_AI = os.environ.get("USE_MOCK_AI", "false").lower() in ("1", "true", "yes")

app = Flask(__name__)
CORS(app)

FALLBACK_REPLIES = [
    "I'm sorry — I'm having trouble reaching the AI service right now. Please try again in a moment.",
    "I can't reach the AI at the moment. Would you like a breathing exercise while we try again?",
    "Temporary service error — I can give quick coping tips until the service returns."
]

def get_fallback_response():
    return random.choice(FALLBACK_REPLIES)

def mock_response(message: str) -> str:
    low_msg = (message or "").lower().strip()
    if "suicid" in low_msg or "kill myself" in low_msg or "i want to die" in low_msg:
        return ("It sounds like you are in serious distress. If you are in immediate danger please call your local emergency number. "
                "If it's safe, consider contacting a crisis line. I can also guide you through grounding or breathing exercises.")
    if "how are you" in low_msg or "how r you" in low_msg:
        return "I'm EthicaMind — I'm here to support you. How are you feeling today?"
    if len(low_msg) < 5:
        return "Thanks for sharing. Tell me a bit more so I can help."
    return "I hear you. It's okay to feel that way. Would you like a breathing exercise or some quick coping tips?"

def try_google_genai(message: str):
    try:
        import google_genai as genai
    except Exception:
        raise
    try:
        client = None
        if hasattr(genai, "Client"):
            try:
                client = genai.Client(api_key=API_KEY)
            except Exception:
                # Some installs use environment key only
                client = genai.Client() if hasattr(genai, "Client") else None
        if client:
            resp = client.chat.create(input=message)
            return str(resp)
        else:
            resp = genai.chat.create(input=message)
            return str(resp)
    except Exception:
        raise

def try_google_generativeai(message: str):
    try:
        import google.generativeai as ga
    except Exception:
        raise
    try:
        if API_KEY:
            try:
                ga.configure(api_key=API_KEY)
            except Exception:
                pass
        if hasattr(ga, "chat"):
            resp = ga.chat.create(model="models/chat-bison-001", messages=[{"author":"user","content":message}])
            if isinstance(resp, dict):
                return (resp.get("candidates") or [{}])[0].get("content", "") or str(resp)
            return str(resp)
        if hasattr(ga, "generate"):
            resp = ga.generate(model="models/text-bison-001", prompt=message)
            if isinstance(resp, dict):
                return (resp.get("candidates") or [{}])[0].get("output") or str(resp)
            return str(resp)
        return str(ga)
    except Exception:
        raise

def send_to_model(message: str) -> str:
    logger.info("Incoming message (len=%d): %s", len(message or ""), message)
    if USE_MOCK_AI:
        logger.info("USE_MOCK_AI enabled: returning mock response.")
        return mock_response(message)

    attempts = [
        ("google_genai", try_google_genai),
        ("google.generativeai", try_google_generativeai),
    ]

    max_attempts = 3
    for attempt_num in range(1, max_attempts + 1):
        logger.info("GenAI call attempt %d for message length %d", attempt_num, len(message))
        for name, func in attempts:
            try:
                logger.info("Attempting client: %s", name)
                result = func(message)
                logger.info("Client %s succeeded.", name)
                if result is None:
                    result = ""
                return str(result)
            except Exception as e:
                logger.error("%s attempt failed: %s", name, str(e))
                logger.error(traceback.format_exc())
        backoff = 1.0 * (2 ** (attempt_num - 1))
        logger.info("Exhausted clients on attempt %d; sleeping %.1fs before retry.", attempt_num, backoff)
        time.sleep(backoff)

    logger.warning("Exhausted GenAI clients; using fallback.")
    return get_fallback_response()

@app.route("/")
def root():
    return "EthicaMind backend is up."

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        body = request.get_json(force=True)
        message = body.get("message") if body else ""
        if not message:
            return jsonify({"type":"error","message":"No message provided."}), 400
        ai_text = send_to_model(message)
        return jsonify({"type":"chat","message":ai_text}), 200
    except Exception as e:
        logger.error("Unhandled exception in /api/chat: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({"type":"error","message":"Internal server error."}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
