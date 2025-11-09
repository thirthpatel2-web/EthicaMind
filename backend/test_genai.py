from dotenv import load_dotenv
import os
load_dotenv()
try:
    import google.generativeai as genai
    print("genai import ok")
except Exception as e:
    print("genai import failed:", e)
    raise SystemExit

API_KEY = os.getenv("ETHICAMIND_API_KEY")
print("Using API_KEY present?:", bool(API_KEY))

try:
    genai.configure(api_key=API_KEY)
    print("configured genai")
    # Try a small chat request (library might accept different call shapes)
    try:
        resp = genai.chat.create(
            model="chat-bison-001",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, can you say hi?"}
            ],
            temperature=0.6,
        )
        print("CHAT RESP (raw):", repr(resp))
    except Exception as inner_e:
        print("genai.chat.create failed:", repr(inner_e))
        # Try alternate API shape (some versions use genai.generate or generativelanguage client)
        try:
            resp2 = genai.generate(
                model="chat-bison-001",
                prompt="Hello"
            )
            print("ALTERNATE RESP (raw):", repr(resp2))
        except Exception as inner2:
            print("alternate generate failed:", repr(inner2))
except Exception as e:
    print("configuration or call failed:", repr(e))
