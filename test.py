import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

print("Current folder:", os.getcwd())
print("Token raw:", repr(token))
print("Token length:", len(token) if token else 0)

if not token:
    print("❌ No token found!")
else:
    print("✅ Token loaded successfully.")