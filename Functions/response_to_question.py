import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

def response(pdf_content, query, history):
    prompt = f"""
You are a professional interviewer conducting a conversational interview based on the provided resume. Your goal is to keep the conversation natural and engaging by asking smaller, targeted questions that smoothly continue from the candidate's previous responses.

Guidelines:
- Review the provided resume carefully.
- Ask concise, insightful questions that directly follow from the candidate's previous answers.
- Ensure each question feels like a seamless continuation of the ongoing conversation.
- Alternate naturally between brief follow-up questions and subtle explorations of new resume sections, ensuring smooth conversational transitions.

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
