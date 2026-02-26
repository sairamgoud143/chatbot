from fastapi import FastAPI, Request
import redis.asyncio as redis
import joblib
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

UPSTASH_URL = os.getenv("UPSTASH_REDIS_URL")
PASSWORD = os.getenv("BOT_PASSWORD")

# Connect to Upstash
r = redis.from_url(UPSTASH_URL)

# Load intent model
model_path = os.path.join(os.path.dirname(__file__), "intent_based_model.pkl")
model = joblib.load(model_path)

app = FastAPI()

# ---------------- Password Verify ---------------- #
@app.post("/verify")
async def verify(data: dict):
    pswd = data.get("password", "")
    if pswd == PASSWORD:
        return {"status": "Access Granted!"}
    return {"status": "Invalid Password"}

# ---------------- Activate Chitti ---------------- #
@app.post("/activate")
async def activate(data: dict):
    user_id = data.get("user_id")
    code_word = data.get("code_word", "").lower()
    if "chitti" not in code_word:
        return {"status": "Code word required!"}
    
    # Store session in Redis (1 hour expiry)
    await r.set(f"{user_id}:active", "true", ex=3600)
    await r.set(f"{user_id}:history", "", ex=3600)
    return {"status": "Chitti Activated!"}

# ---------------- Process Command ---------------- #
@app.post("/command")
async def command(data: dict):
    user_id = data.get("user_id")
    command = data.get("command", "")
    if not command:
        return {"response": "No command provided"}

    # Check if user session is active
    active = await r.get(f"{user_id}:active")
    if not active:
        return {"response": "Activate Chitti first!"}

    # Predict intent
    intent = model.predict([command])[0] if model else "Unknown"
    response = ""

    if intent == "music":
        response = f"🎵 Simulating music play for: {command}"
    elif intent == "news":
        response = "📰 Latest News: India Tech Growth Rising"
    elif intent == "website":
        site = command.split()[-1]
        response = f"🌐 Open link: https://{site}.com"
    else:
        response = "Sorry, I didn't understand the command."

    # Update chat history in Redis
    history = await r.get(f"{user_id}:history") or ""
    history += f"User: {command}\nChitti: {response}\n"
    await r.set(f"{user_id}:history", history)

    return {"response": response, "history": history}
