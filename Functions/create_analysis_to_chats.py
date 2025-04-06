import  json
import os
from dotenv import load_dotenv
from anthropic import AnthropicVertex  # Ensure your AnthropicVertex package is installed and configured
# Load environment variables and set credentials
load_dotenv()
# Build credentials from environment variables and write to a file
credentials_json = {
    "type": os.getenv("type"),
    "project_id": os.getenv("project_id"),
    "private_key_id": os.getenv("private_key_id"),
    "private_key": os.getenv("private_key").replace('\\n', '\n'),  # Ensure correct newline handling
    "client_email": os.getenv("client_email"),
    "client_id": os.getenv("client_id"),
    "auth_uri": os.getenv("auth_uri"),
    "token_uri": os.getenv("token_uri"),
    "auth_provider_x509_cert_url": os.getenv("auth_provider_x509_cert_url"),
    "client_x509_cert_url": os.getenv("client_x509_cert_url"),
    "universe_domain": os.getenv("universe_domain")
}

with open("credentials.json", "w") as f:
    json.dump(credentials_json, f, indent=2)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"credentials.json"
project_id = os.getenv("project_id")
region = os.getenv("region")
client = AnthropicVertex(project_id=project_id, region=region)
# Function to generate a structured interview scorecard using Anthropic's evaluation
def generate_scorecard(conversation: dict) -> dict:
    # Hardcoded evaluation criteria for interviews
    # Note: The evaluation for technical knowledge and problem solving (domain expertise) should be more elaborate
    hardcoded_criterias = [
        {
            "parameter": "Technical Knowledge",
            "top_score": 100,
            "marking_type": "Numeric",
            "scoring_guide": "Evaluate the candidate's in-depth technical and domain expertise. Provide detailed evidence and justification."
        },
        {
            "parameter": "Problem Solving",
            "top_score": 100,
            "marking_type": "Numeric",
            "scoring_guide": "Assess the candidate's analytical skills and ability to solve complex problems with comprehensive explanation."
        },
        {
            "parameter": "Communication",
            "top_score": 80,
            "marking_type": "Numeric",
            "scoring_guide": "Evaluate clarity, articulation, and conciseness in communication. Provide brief evidence."
        },
        {
            "parameter": "Interpersonal Skills",
            "top_score": 80,
            "marking_type": "Pass/Fail",
            "scoring_guide": "Assess teamwork, collaboration, and overall soft skills with minimal elaboration."
        }
    ]
    
    # System prompt instructing for only JSON response and clear instructions for elaboration levels
    system_prompt = """
    You are an expert evaluator for technical interviews. Evaluate the following conversation based on these hardcoded criteria:
    
    - Technical Knowledge (Max Score: 100, Numeric): Provide an in-depth analysis of the candidate's technical and domain expertise.
    - Problem Solving (Max Score: 100, Numeric): Deliver a detailed explanation of the candidate's problem-solving abilities.
    - Communication (Max Score: 80, Numeric): Provide a concise evaluation of communication skills.
    - Interpersonal Skills (Max Score: 80, Pass/Fail): Offer a brief assessment of soft skills.
    
    Your response MUST be a valid JSON object with no additional text.
    Follow exactly this JSON format:
    {
      "evaluations": [
        {
          "parameter": "<Parameter Name>",
          "result": "<'Pass'/'Fail' or numeric score>",
          "score": "<Score>/<Max Score>",
          "evidence": ["<evidence text>"]
        }
      ],
      "Overall_score": "<Total Score>/<Total Max Score>",
      "Overall_grammar": "<Assessment of grammar quality>",
      "Overall_accent": "<Assessment of tone and communication>",
      "Overall_analysis": "<Overall interview analysis summary>"
    }
    """
    
    # Format the conversation transcript strictly from the stored messages
    conversation_text = "\n".join([
        f"User: {m['user']}\nAssistant: {m['response']}" for m in conversation.get('messages', [])
    ])
    
    analysis_prompt = f"""
    Evaluate the following interview conversation based on the criteria above. Provide more elaborate analysis for Technical Knowledge and Problem Solving, while keeping Communication and Interpersonal Skills evaluation concise.
    
    **Conversation Transcript:**
    {conversation_text}
    """
    
    full_prompt = system_prompt + "\n" + analysis_prompt
    
    try:
        # Send evaluation request to Anthropic
        response = client.messages.create(
            model="claude-3-5-sonnet-v2@20241022",
            max_tokens=3000,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": full_prompt
            }]
        )
        claude_response_text = response.content[0].text
        
        # Attempt to parse the JSON response
        try:
            parsed_scores = json.loads(claude_response_text)
        except json.JSONDecodeError as json_error:
            return {
                "error": f"JSON Parsing Error: {str(json_error)}",
                "raw_response": claude_response_text,
                "message": "Anthropic's response was not in valid JSON format."
            }
        
        scorecard_result = {
            "conversation_id": conversation.get("_id", "unknown_id"),
            "claude_analysis": parsed_scores
        }
        return scorecard_result
    
    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to generate scorecard"
        }
