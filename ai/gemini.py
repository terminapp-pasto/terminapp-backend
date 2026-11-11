"""Connection to the Gemini API.

This is the only file that knows how to talk to the AI provider. If the
provider ever changes, only this file has to be replaced.
"""

import json
import urllib.error
import urllib.request

import config

REQUEST_TIMEOUT_SECONDS = 30
ERROR_DETAIL_MAX_LENGTH = 500


class AIError(Exception):
    """The AI could not answer: missing key, no connection, or the service returned an error."""


def generate_content(contents, system_instructions, tool_declarations):
    """Sends the conversation to Gemini and returns the model's reply message."""
    if not config.GEMINI_API_KEY:
        raise AIError("Missing environment variable GEMINI_API_KEY")

    body = {
        "systemInstruction": {"parts": [{"text": system_instructions}]},
        "contents": contents,
        "tools": [{"functionDeclarations": tool_declarations}],
    }
    request = urllib.request.Request(
        config.GEMINI_API_URL.format(model=config.GEMINI_MODEL),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": config.GEMINI_API_KEY},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:ERROR_DETAIL_MAX_LENGTH]
        raise AIError(f"Gemini answered with status {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise AIError(f"Could not connect to Gemini: {error.reason}") from error

    candidates = data.get("candidates") or []
    if not candidates or "content" not in candidates[0]:
        raise AIError("Gemini returned no answer")
    return candidates[0]["content"]
