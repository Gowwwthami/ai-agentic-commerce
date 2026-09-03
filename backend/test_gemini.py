from google import genai
from config import LLM_API_KEY


if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY is not configured")


client = genai.Client(
    api_key=LLM_API_KEY
)


response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Reply with exactly: Gemini connection successful"
)


print(response.text)