# backend/app.py
import os
import time
import logging
from typing import Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# --- Logging ---------------------------------------------------------------
logger = logging.getLogger("ethicamind")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)

# --- Config ---------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# Load .env if present (useful for local dev)
load_dotenv(os.path.join(ROOT_DIR, ".env"))
ETHICAMIND_API_KEY = os.environ.get("ETHICAMIND_API_KEY")  # expected env var

logger.info("DEBUG: ETHICAMIND_API_KEY present?: %s", bool(ETHICAMIND_API_KEY))
if ETHICAMIND_API_KEY:
    # Masked for logs
    logger.info("DEBUG: masked key: %s", ETHICAMIND_API_KEY[:6] + "..." + ETHICAMIND_API_KEY[-4:])

# --- Flask app ------------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


# --- GenAI calling helpers -----------------------------------------------
def send_to_model(message: str) -> Optional[str]:
    """
    Try supported GenAI clients in order. On success return text (string).
    On total failure return None.
    Full exceptions are logged server-side.
    """
    # 1) try google_genai (newer package often named google-genai)
    try:
        import google_genai as genai  # type: ignore
        logger.info("Attempting call with google_genai client.")
        # Example: adapt this to the actual call shape you used during local dev.
        # This is a minimal example calling a hypothetical client method:
        client = genai.Client(api_key=ETHICAMIND_API_KEY) if hasattr(genai, "Client") else None
        if client:
            # NOTE: change to your actual call signature used locally if different.
            resp = client.chat(message=message)
            # try common attribute names
            ai_text = getattr(resp, "text", None) or getattr(resp, "content", None) or str(resp)
            return ai_text
        # If no client class available, fall through to exception
        raise RuntimeError("google_genai client object not available (stub).")
    except Exception:
        logger.exception("google_genai attempt failed")

    # 2) try google.generativeai (older package / google-generativeai)
    try:
        import google.generativeai as ga  # type: ignore
        logger.info("Attempting call with google.generativeai client.")
        # Example usage: adapt to your code
        # ga.configure(api_key=ETHICAMIND_API_KEY)
        # resp = ga.generate_text(model="models/xxx", input=message)
        # ai_text = resp.text or resp.output or str(resp)
        # For safety here we'll attempt multiple known shapes:
        if hasattr(ga, "configure"):
            try:
                ga.configure(api_key=ETHICAMIND_API_KEY)
            except Exception:
                pass
        # If the library has a simple generate function:
        if hasattr(ga, "generate_text"):
            try:
                resp = ga.generate_text(input=message)
                ai_text = getattr(resp, "text", None) or getattr(resp, "output", None) or str(resp)
                return ai_text
            except Exception:
                logger.exception("generate_text call using google.generativeai failed")
        # else fallthrough
        raise RuntimeError("google.generativeai call not implemented in stub.")
    except Exception:
        logger.exception("google.generativeai attempt failed")

    # No supported client succeeded
    return None


def call_genai_with_retries(message: str, max_attempts: int = 3, base_delay: float = 1.0) -> str:
    """
    Wraps send_to_model with retries + exponential backoff.
    Returns final AI text OR a safe fallback message.
    """
    for attempt in range(1, max_attempts + 1):
        logger.info("GenAI call attempt %d for message length %d", attempt, len(message))
        try:
            ai_text = send_to_model(message)
            if ai_text:
                logger.info("GenAI client succeeded.")
                return ai_text
            logger.warning("No supported GenAI client available (or all calls failed).")
        except Exception:
            logger.exception("Unhandled exception while calling send_to_model")

        sleep_for = base_delay * (2 ** (attempt - 1))
        logger.info("Sleeping %.1fs before next retry...", sleep_for)
        time.sleep(sleep_for)

    logger.warning("Exhausted GenAI retries; using fallback.")
    return "Sorry — I'm having trouble reaching the AI service; please try again later."


# --- Simple crisis/triage detector (very small example) --------------------
CRISIS_KEYWORDS = {"kill", "suicide", "die", "ending", "end my life", "harm myself"}

def check_for_crisis(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in CRISIS_KEYWORDS)


# --- Routes ---------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return "EthicaMind backend is up.", 200


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    # OPTIONS requests for preflight will be handled by CORS library; treat them
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"message": "Invalid JSON", "type": "error"}), 400

    message = body.get("message", "").strip() if isinstance(body, dict) else ""
    logger.info("Incoming message (len=%d): %s", len(message), message[:120])

    if not message:
        return jsonify({"message": "Please provide a message.", "type": "error"}), 400

    # Crisis triage: respond with special type that frontend uses to open modal
    if check_for_crisis(message):
        logger.warning("Crisis keyword detected; triggering triage.")
        return jsonify({"message": "Crisis detected", "type": "CRISIS_TRIAGE"}), 200

    # Call the GenAI stack (with retries). This returns text (either AI or fallback).
    ai_text = call_genai_with_retries(message)

    # Return consistent shape
    return jsonify({"message": ai_text, "type": "chat"}), 200


# --- Run locally ----------------------------------------------------------
if __name__ == "__main__":
    # Local debug run
    port = int(os.environ.get("PORT", 5000))
    debug_flag = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_flag)
