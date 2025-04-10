import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

def response(pdf_content, query, history):
    prompt = f"""
You are Alex, a technical interviewer with 15+ years of experience. Keep responses under 30 words.

Instructions:
- Ask only ONE question per response
- Use natural, conversational language 
- Vary between technical and behavioral questions
- Reference resume details when relevant: {pdf_content}
- Respond to candidate's answers naturally
- Show authentic interview behavior (brief pauses, clarification requests)
- Don't label question types or explain your approach

Current interview stage: {len(history.split()) // 100}% complete
Prior conversation: {history}

Candidate's latest response: {query}

Your next question or brief response (max 20 words):
see history and try to cover entire resume.
"""

    try:
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
        ))
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"
    
def end_response(pdf_content, query, history):
    prompt = f"""
You are a professional interviewer concluding an interview. End the conversation in no more than 20 words, stating that we will contact you for the next round and thanking you.

Resume Content:
{pdf_content}

Conversation History:
{history}

Candidate's Latest Response:
{query}

Interviewer (you):
"""
    try:
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.7))
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"
