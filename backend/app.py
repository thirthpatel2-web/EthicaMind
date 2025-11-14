# backend/app.py
import os
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env (if exists)
load_dotenv()

# --- Logging ---
logger = logging.getLogger("ethicamind")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Config ---
ETHICAMIND_API_KEY = os.getenv("ETHICAMIND_API_KEY") or os.getenv("ETHICAMIND_API_KEY".upper())
DEMO_MODE = os.getenv("ETHICAMIND_DEMO_MODE", "false").lower() in ("1", "true", "yes")

# Create Flask app
app = Flask(__name__)
# Allow CORS from your frontend (adjust origin if needed)
CORS(app, origins=["http://localhost:3000", "https://ethica-mind.vercel.app", "*"])

# --- Triage system (detect crisis) ---
def TriageSystem(message: str):
    if not message:
        return None
    m = message.lower()
    CRISIS_LIST = [
        "kill myself", "i want to die", "want to die", "no reason to live",
        "suicide", "i will kill myself", "end my life", "i can't go on"
    ]
    for keyword in CRISIS_LIST:
        if keyword in m:
            return True
    return None

# --- Ethical Guardrail (deny list) ---
def EthicalGuardrail(message: str):
    if not message:
        return None
    m = message.lower()
    DENY_LIST = [
        "diagnose me", "prescription", "what pills", "medical advice",
        "how to perform surgery", "how to treat disease", "give me a diagnosis"
    ]
    for kw in DENY_LIST:
        if kw in m:
            return (
                "I am a wellness assistant, not a medical professional. "
                "I cannot provide a diagnosis or medical advice. Please consult a doctor."
            )
    return None

# ----------------------------
# Model-calling helpers
# ----------------------------

def send_to_model(message: str):
    """
    Try multiple client styles to call a Google GenAI / Gemini-style API.
    This function attempts to work with either:
     - google_genai (google-genai) library
     - google.generativeai library (older style)
    If your project uses a different client pattern, replace the internals of this
    function with the exact call shape you already had.
    Returns: str (AI response text)
    Raises: Exception on total failure.
    """
    # Quick demo-mode shortcut: return canned reply (if you want guaranteed deterministic behavior)
    if DEMO_MODE:
        logger.info("DEMO_MODE enabled: returning canned demo response.")
        return "Hello — thanks for checking in. I'm EthicaMind, here to support you."

    # 1) Try google_genai (package name: google_genai)
    try:
        import google_genai as genai  # installed on Render in your logs
        # try if there is a client already created at module-level
        client = globals().get("genai_client", None)

        # there are different calling patterns; try module-level chat.create then client.chat.create
        try:
            if client:
                logger.info("Using genai_client.chat.create(...)")
                resp = client.chat.create(model="chat-bison-001", messages=[{"role":"user","content":message}])
            else:
                logger.info("Using google_genai.chat.create(...)")
                resp = genai.chat.create(model="chat-bison-001", messages=[{"role":"user","content":message}])
        except Exception as e:
            # try alternate model id or method name depending on SDK version
            logger.exception("First google_genai attempt failed: %s", e)
            # fallback attempt (some versions expose generate/text methods)
            if client and hasattr(client, "generate"):
                resp = client.generate(model="text-bison-001", prompt=message)
            else:
                raise

        # Try common extraction patterns:
        # pattern A: resp.output[0].content[0].text
        try:
            out = resp.output[0].content[0].text
            return out
        except Exception:
            pass

        # pattern B: resp.choices[0].message.content[0].text
        try:
            out = resp.choices[0].message.content[0].text
            return out
        except Exception:
            pass

        # pattern C: resp.text or str(resp)
        if hasattr(resp, "text"):
            return resp.text
        return str(resp)
    except Exception as ex:
        logger.exception("google_genai attempt failed: %s", ex)

    # 2) Try google.generativeai (older package name)
    try:
        import google.generativeai as ga
        if ETHICAMIND_API_KEY:
            try:
                # older style init
                ga.configure(api_key=ETHICAMIND_API_KEY)
            except Exception:
                pass
        # Attempt a chat call (shape may vary)
        try:
            resp = ga.chat.create(model="chat-bison-001", messages=[{"role":"user","content":message}])
            # extraction:
            try:
                return resp.output[0].content[0].text
            except Exception:
                pass
            try:
                return resp.choices[0].message.content[0].text
            except Exception:
                pass
            return str(resp)
        except Exception as inner:
            logger.exception("google.generativeai chat.create failed: %s", inner)
            raise inner
    except Exception as ex2:
        logger.exception("google.generativeai attempt failed: %s", ex2)

    # If we reach here, we could not call any supported GenAI client
    raise RuntimeError("No supported GenAI client available (or all calls failed).")

def call_genai_with_retries(message: str, max_retries: int = 3, initial_delay: float = 1.0):
    """
    Retry wrapper with exponential backoff.
    Returns: text (str) on success, or None if exhausted.
    """
    delay = initial_delay
    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            logger.info("GenAI call attempt %d for message length %d", attempt, len(message))
            ai_text = send_to_model(message)
            # if send_to_model returned something (non-empty), return it
            if ai_text is not None:
                return ai_text
        except Exception as e:
            # Log full exception so Render logs show the root cause
            logger.exception("GenAI call failed on attempt %d: %s", attempt, e)
            # If this was the last attempt, fall through to fallback
            if attempt >= max_retries:
                logger.warning("Exhausted GenAI retries (%d). Will use fallback.", max_retries)
                return None
            # Wait then retry (exponential backoff)
            logger.info("Sleeping %.1fs before next retry...", delay)
            time.sleep(delay)
            delay *= 2.0
    return None

# ----------------------------
# Flask endpoint
# ----------------------------
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    data = request.get_json(silent=True) or {}
    message = data.get("message", "") if isinstance(data, dict) else ""

    # immediate empty message handling
    if not message:
        return jsonify({"type": "chat", "message": "Please enter a message."})

    # 1) Triage crisis check
    if TriageSystem(message):
        logger.info("TriageSystem triggered for message: %s", message[:80])
        return jsonify({"type": "CRISIS_TRIAGE"})

    # 2) Guardrail check
    guard_resp = EthicalGuardrail(message)
    if guard_resp is not None:
        logger.info("EthicalGuardrail triggered for message: %s", message[:80])
        return jsonify({"type": "chat", "message": guard_resp})

    # 3) If demo-mode is enabled, return canned response (deterministic demo)
    if DEMO_MODE:
        demo_text = "I hear you. It's completely okay to feel stressed sometimes. Be kind to yourself today."
        return jsonify({"type": "chat", "message": demo_text})

    # 4) Call GenAI with retries
    ai_text = call_genai_with_retries(message, max_retries=3, initial_delay=1.0)

    if ai_text is None:
        # final friendly fallback (frontend will display this)
        fallback_text = "Sorry — I'm having trouble reaching the AI service; please try again later."
        return jsonify({"type": "chat", "message": fallback_text})

    # 5) success
    return jsonify({"type": "chat", "message": ai_text})

# Root route (optional)
@app.route("/", methods=["GET"])
def index():
    return jsonify({"ok": True, "message": "EthicaMind backend"}), 200

# Run locally
if __name__ == "__main__":
    logger.info("Starting EthicaMind Flask app (local dev)")
    # When run by gunicorn on Render, this block is not executed.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
