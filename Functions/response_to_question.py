import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

def response(pdf_content, query, history):
    prompt = f"""
You are a highly experienced and discerning interviewer conducting a tough, in-depth conversational interview based on the candidate's resume. Your goal is to challenge the candidate with **technically demanding, thought-provoking** questions while keeping the tone conversational.

Guidelines:
- Carefully analyze the provided resume to identify areas for deeper exploration.
- Ask difficult and insightful questions that require the candidate to demonstrate expert-level understanding, problem-solving, and reasoning.
- Make your responses feel like a natural conversation continuation by:
  - Starting with brief acknowledgments like "I see," "Interesting," "That makes sense," or "Good point"
  - Using transitional phrases like "Let's shift focus a bit," "Building on that," or "Speaking of your work at [company]"
  - Occasionally referencing the candidate's previous answers
- Ensure the conversation feels natural and continuous, like a real interview — avoid unrelated topic jumps.
- Progressively increase complexity and depth as the interview unfolds.
- Limit each question to no more than 20 words.
- Include a diverse mix of questions, such as:
  - Coding challenges or function implementations tied to the candidate's tech stack.
  - Real-world scenarios and trade-off discussions.
  - System design and theoretical deep-dives.

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
def end_response(pdf_content, query, history):
    prompt = f"""
You are a highly professional interviewer concluding a **challenging and insightful** interview based on the candidate's resume. Your goal is to **end the conversation gracefully** by summarizing key points, providing constructive feedback, and thanking the candidate for their time.

Guidelines:
- Reflect briefly on the candidate's performance and highlight any strengths or notable answers.
- Provide polite and professional feedback or suggestions for improvement if appropriate.
- End the conversation on a positive and respectful note.
- Thank the candidate for participating and let them know what the next steps might be (optional).

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
