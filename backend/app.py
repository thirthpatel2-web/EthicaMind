from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Try new Google GenAI SDK (google-genai)
GENAI_SDK_AVAILABLE = True
try:
    from google import genai
except Exception:
    GENAI_SDK_AVAILABLE = False

load_dotenv()

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("ETHICAMIND_API_KEY", None)

CRISIS_LIST = [
    "kill myself", "want to die", "i want to die", "no reason to live", "suicid", "end my life",
    "i'm going to kill myself", "hurting myself", "i want to end it", "thoughts of suicide"
]

DENY_LIST = [
    "diagnose me", "prescription", "medical advice", "what pills", "what medication", "give me medication",
    "should i take", "dosage"
]

def TriageSystem(message: str):
    if not message:
        return None
    lower = message.lower()
    for kw in CRISIS_LIST:
        if kw in lower:
            return True
    return None

def EthicalGuardrail(message: str):
    if not message:
        return None
    lower = message.lower()
    for kw in DENY_LIST:
        if kw in lower:
            return ("I am a wellness assistant, not a medical professional. "
                    "I cannot provide a diagnosis or medical advice. Please consult a doctor.")
    return None

# Diagnostics
print("DEBUG: google-genai SDK available?:", GENAI_SDK_AVAILABLE)
print("DEBUG: ETHICAMIND_API_KEY present?:", bool(API_KEY))
if API_KEY:
    try:
        print("DEBUG: masked key:", API_KEY[:6] + "..." + API_KEY[-4:])
    except Exception:
        pass

genai_client = None
if GENAI_SDK_AVAILABLE and API_KEY:
    try:
        genai_client = genai.Client(api_key=API_KEY)
        print("✅ google-genai client created.")
    except Exception as e:
        print("⚠️ Failed to initialize google-genai client:", repr(e))
        genai_client = None

@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json() or {}
    user_message = payload.get("message", "")
    if not isinstance(user_message, str):
        return jsonify({"type": "chat", "message": "Invalid input."}), 400

    # 1) Triage check
    if TriageSystem(user_message):
        return jsonify({"type": "CRISIS_TRIAGE"})

    # 2) Guardrail check
    guard = EthicalGuardrail(user_message)
    if guard:
        return jsonify({"type": "chat", "message": guard})

    # 3) Call GenAI if client exists, otherwise fallback
    ai_response_text = None

    if genai_client is None:
        ai_response_text = (
            "Thanks for sharing. I'm here to support your wellness — could you tell me a little more about what's on your mind?"
        )
    else:
        try:
            # Adjust model_name if needed for your account/permission
            model_name = "gemini-2.5-flash"
            system_prompt = "You are EthicaMind, a compassionate wellness assistant. Keep responses short and supportive."
            resp = genai_client.models.generate_content(
                model=model_name,
                contents=[system_prompt, user_message],
            )
            # try common attributes for text
            ai_response_text = getattr(resp, "text", None) or getattr(resp, "output", None) or str(resp)
        except Exception as e:
            print("GenAI call exception:", repr(e))
            ai_response_text = "Sorry — I'm having trouble reaching the AI service; please try again later."

    return jsonify({"type": "chat", "message": ai_response_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
