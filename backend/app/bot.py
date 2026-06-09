import google.generativeai as genai
from app.config import settings
from app.policies import get_policy_document_text
from typing import List
from app.schemas import ChatMessage

# Initialize Gemini Client
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    # We will log a warning or raise an exception in production,
    # but let's allow initialization so startup doesn't fail immediately 
    # if the key is not set yet.
    pass

# System Prompt Template
SYSTEM_PROMPT = """
You are HRBot, the official HR Policy Assistant for TechNovance Solutions Pvt. Ltd.

YOUR RULES — FOLLOW THESE WITHOUT EXCEPTION:
1. ONLY answer from the HR policy document provided below. Do NOT use any outside knowledge about HR practices, other companies, or general policies.
2. ALWAYS cite the specific policy section in your answer. Format the citation clearly, for example: "Per Section X.Y (Policy Name)..." or "Per Section X — [Name]...".
3. If a question is NOT covered in the policy document, respond EXACTLY:
   "This is not covered in the policy document. Please reach out to HR directly at hr@technovance.com or call +91-40-2345-6789."
   Do NOT try to answer it using external information or generate a helpful-sounding but unsanctioned answer.
4. If someone asks about their PERSONAL data (their leave balance, their salary, their appraisal score, their joining date, etc.), say:
   "I can only provide policy information. For personal data, please log in to the HRMS portal at https://hrms.technovance.internal or contact HR at hr@technovance.com."
5. For SCENARIO-BASED questions (e.g., "I have a doctor's appointment tomorrow, what leave should I apply?"), identify the correct leave type from the policy document, explain the eligibility, and mention the approval process.
6. Keep answers concise but complete. Use bullet points for multi-part answers.
7. Be professional, warm, and helpful. You represent the HR department.
8. If a question is ambiguous, ask ONE clarifying question before answering.

THE COMPLETE HR POLICY DOCUMENT:
{policy_document}
"""

def get_system_instruction() -> str:
    """
    Builds the system instruction by injecting the policy document text.
    """
    policy_doc = get_policy_document_text()
    return SYSTEM_PROMPT.format(policy_document=policy_doc)

def generate_bot_response(message: str, history: List[ChatMessage]) -> str:
    """
    Queries the Gemini API using the model with system instruction.
    Supports multi-turn chat history.
    """
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        raise ValueError("GEMINI_API_KEY is not configured. Please set a valid key in the .env file.")
        
    system_instruction = get_system_instruction()
    
    # Initialize the generative model with the strict system instruction
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_instruction
    )
    
    # Format the chat history for Gemini (converting role 'assistant' to 'model')
    # Limit history to the last 10 messages (5 turns) to keep context fast and optimized
    gemini_history = []
    for msg in history[-10:]:
        role = "user" if msg.role == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg.content]})
        
    # Start a chat session with the historical context
    chat = model.start_chat(history=gemini_history)
    
    # Send the user message and return the text response
    response = chat.send_message(message)
    return response.text
