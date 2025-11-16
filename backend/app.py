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
# --- diagnostic send_to_model (temporary) ---------------------------------
# --- GenAI calling helpers (robust import + model selection) ----------------
import json
from google.genai import errors as _ga_errors  # type: ignore  # optional, used in some clients

def send_to_model(message: str) -> str | None:
    """
    Try available Google GenAI clients in order:
      1) google.genai (preferred modern package)
      2) google_genai (some installs expose this)
      3) google.generativeai (older)
    Returns generated text or None on no-client/error.
    All exceptions are logged server-side.
    """
    # pick model names that are known to exist on your account (diagnostic list earlier showed many).
    preferred_models = [
        "gemini-2.5-flash",           # if available on your paid plan
        "gemini-2.5-flash-lite",      # cheaper
        "gemini-pro-latest",
        "gemini-flash-latest",
        "gemini-2.0-flash"            # fallback older
    ]

    # 1) try google.genai (recommended)
    try:
        import google.genai as genai  # type: ignore
        logger.info("Using google.genai client.")
        client = genai.Client(api_key=os.getenv("ETHICAMIND_API_KEY"))

        # Try preferred models in order until one works
        for model_name in preferred_models:
            try:
                logger.info("Attempt generate_content with model: %s", model_name)
                resp = client.models.generate_content(model=model_name, contents=message)
                # Extract text carefully
                ai_text = ""
                # resp.candidates is typical shape; adapt if different
                if getattr(resp, "candidates", None):
                    for part in getattr(resp.candidates[0].content, "parts", []):
                        if hasattr(part, "text"):
                            ai_text += part.text
                # if other shape: try resp.output or resp.text
                if not ai_text and hasattr(resp, "output"):
                    ai_text = getattr(resp, "output", "") or ""
                if ai_text:
                    return ai_text.strip()
            except Exception as e:
                # Log the candidate failure and continue to next model
                logger.exception("Generate attempt failed for model %s; trying next model.", model_name)
        logger.warning("google.genai client available but no model succeeded.")
    except Exception:
        logger.exception("google.genai import or call failed.")

    # 2) try older package name google_genai (some installs expose this top-level)
    try:
        import google_genai as genai  # type: ignore
        logger.info("Using google_genai client.")
        client = genai.Client(api_key=os.getenv("ETHICAMIND_API_KEY"))
        # best-effort call (names may differ)
        try:
            resp = client.models.generate_content(model=preferred_models[0], contents=message)
            ai_text = ""
            if getattr(resp, "candidates", None):
                for part in getattr(resp.candidates[0].content, "parts", []):
                    if hasattr(part, "text"):
                        ai_text += part.text
            if ai_text:
                return ai_text.strip()
        except Exception:
            logger.exception("google_genai call failed.")
    except Exception:
        logger.info("google_genai not installed or import failed.")

    # 3) try google.generativeai (older library)
    try:
        import google.generativeai as ga  # type: ignore
        logger.info("Using google.generativeai client.")
        # usage varies by version; example:
        # ga.configure(api_key=os.getenv("ETHICAMIND_API_KEY"))
        # resp = ga.generate_text(model="some-model", prompt=message)
        # adapt to the specific version you installed
        raise RuntimeError("google.generativeai path not implemented - update here if needed")
    except Exception:
        logger.exception("google.generativeai attempt failed or is unimplemented.")

    # nothing worked
    return None


def call_genai_with_retries(message: str, max_attempts: int = 3, base_delay: float = 1.0) -> str:
    """
    Wrap send_to_model with retries + exponential backoff.
    Returns final AI text OR a safe fallback message.
    """
    for attempt in range(1, max_attempts + 1):
        logger.info(f"GenAI call attempt {attempt} for message length {len(message)}")
        try:
            ai_text = send_to_model(message)
            if ai_text:
                logger.info("GenAI client succeeded.")
                return ai_text
            logger.warning("No supported GenAI client available (or all calls failed).")
        except Exception:
            logger.exception("Unhandled exception while calling send_to_model")

        # backoff
        sleep_for = base_delay * (2 ** (attempt - 1))
        logger.info(f"Sleeping {sleep_for:.1f}s before next retry...")
        time.sleep(sleep_for)

    # Exhausted retries -> fallback
    logger.warning("Exhausted GenAI retries; using fallback.")
    fallback_text = "Sorry — I'm having trouble reaching the AI service; please try again later."
    return fallback_text
# --- end GenAI helpers ---

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
