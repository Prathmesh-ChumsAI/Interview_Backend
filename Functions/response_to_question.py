import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

def response(pdf_content, query, history):
    prompt = f"""
You are a professional interviewer conducting a conversational interview based on the provided resume. Your goal is to maintain a natural, engaging, and fluid dialogue.

Guidelines:
- Review the provided resume carefully.
- Ask insightful questions that naturally follow from the candidate's previous responses (conversation history).
- Alternate smoothly between follow-up questions to deepen the current topic and new questions to explore different areas of the resume.
- Maintain continuity and make the conversation feel seamless, like a real interview.

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

