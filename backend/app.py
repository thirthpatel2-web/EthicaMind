# --- Paste / replace this code where your existing send_to_model + call_genai_with_retries live ---

import logging
import time

logger = logging.getLogger("ethicamind")
logger.setLevel(logging.INFO)

def send_to_model(message: str) -> str | None:
    """
    Try supported GenAI clients in order. If a client call fails, log full exception
    server-side and continue to next. On success return text. On total failure return None.
    """
    # try google-genai (newer package name)
    try:
        import google_genai as genai  # type: ignore
        logger.debug("Attempting call with google_genai client")
        # --- example use; adjust to your actual call method if different ---
        # response = genai.some_client_call(...) 
        # ai_text = response.text or response.output
        # For safety, guard with try/except around the real call:
        # ai_text = ... 
        # return ai_text
        raise RuntimeError("replace this stub with your real google_genai call")
    except Exception as e:
        # Log full traceback to server logs, do not return to client
        logger.exception("google_genai attempt failed")
    
    # try google.generativeai (older client)
    try:
        import google.generativeai as ga  # type: ignore
        logger.debug("Attempting call with google.generativeai client")
        # ... place your call here similar to above ...
        raise RuntimeError("replace this stub with your real google.generativeai call")
    except Exception as e:
        logger.exception("google.generativeai attempt failed")

    # If you reach here, no GenAI client succeeded
    return None


def call_genai_with_retries(message: str, max_attempts: int = 3, base_delay: float = 1.0) -> str:
    """
    Wrap send_to_model with retries + exponential backoff.
    Returns final AI text OR a safe fallback message.
    Full exceptions are logged server-side.
    """
    for attempt in range(1, max_attempts + 1):
        logger.info(f"GenAI call attempt {attempt} for message length {len(message)}")
        try:
            ai_text = send_to_model(message)
            if ai_text:
                logger.info("GenAI client succeeded.")
                return ai_text
            # if send_to_model returned None, it means the clients were not available
            logger.warning("No supported GenAI client available (or all calls failed).")
        except Exception:
            # log unexpected error and continue (we don't want to crash the route)
            logger.exception("Unhandled exception while calling send_to_model")

        # backoff
        sleep_for = base_delay * (2 ** (attempt - 1))
        logger.info(f"Sleeping {sleep_for:.1f}s before next retry...")
        time.sleep(sleep_for)

    # Exhausted retries -> fallback
    logger.warning("Exhausted GenAI retries; using fallback.")
    # Friendly fallback text for users (do not expose tracebacks)
    fallback_text = "Sorry — I'm having trouble reaching the AI service; please try again later."
    return fallback_text

# --- End snippet ---
