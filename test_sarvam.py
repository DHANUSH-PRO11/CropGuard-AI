import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

# Load SARVAM_API_KEY from .env
load_dotenv()

api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise ValueError("SARVAM_API_KEY not found in environment.")

# Initialize the Sarvam AI client
client = SarvamAI(api_subscription_key=api_key)

# Make a chat completion call
response = client.chat.completions(
    messages=[
        {"role": "user", "content": "Hello! Reply with a brief greeting."}
    ],
    model="sarvam-105b-conversations"
)

# Print the reply
print(response.choices[0].message.content)
