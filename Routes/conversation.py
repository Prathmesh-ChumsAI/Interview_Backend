import os
import re
import json
import base64
import fitz  # PyMuPDF
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from google.cloud import texttospeech
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from anthropic import AnthropicVertex  # Ensure your AnthropicVertex package is installed and configured
from Functions.response_to_question import response,end_response  # Import your response function
from Functions.extract_text_from_pdf import extract_text_from_bytes  # Import your PDF extraction function
from Functions.create_analysis_to_chats import generate_scorecard  # Import your scorecard generation function
from cloudinary import uploader
import cloudinary
import asyncio
from typing import Dict, List
router = APIRouter()
import tempfile
  

# Load environment variables and set credentials
load_dotenv()
# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

active_connections: Dict[str, List[WebSocket]] = {}  # Track active WebSocket connections by file_name

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
async def upload_audio_to_cloudinary(audio_base64: str) -> str:
    temp_file_path = None
    try:
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
            temp_file_path = temp_audio.name
            # Decode base64 and write to temp file
            audio_binary = base64.b64decode(audio_base64)
            temp_audio.write(audio_binary)
        
        # File is now closed, upload to Cloudinary
        result = cloudinary.uploader.upload(
            temp_file_path,
            resource_type="auto",
            folder="audio_responses"
        )
        
        return result['secure_url']
    
    except Exception as e:
        raise Exception(f"Error uploading to Cloudinary: {str(e)}")
    
    finally:
        # Clean up temp file in finally block to ensure it always happens
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_file_path}: {str(e)}")

# Dictionaries to store extracted PDF text and chat history keyed by filename
extracted_texts = {}
chat_histories = {}



# Endpoint to upload a PDF file and extract its text
@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.")
    
    contents = await file.read()
    try:
        text_content = await run_in_threadpool(extract_text_from_bytes, contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    extracted_texts[file.filename] = text_content
    chat_histories[file.filename] = ""  # Initialize empty chat history for the file
    return {"message": "File successfully processed", "file": file.filename}

# Endpoint for chat: uses a response function (assumed to be defined elsewhere)
# @router.get("/chat")
# async def chat(file_name: str, query: str):
#     if file_name not in extracted_texts:
#         raise HTTPException(status_code=404, detail="Extracted text for the requested file not found.")
    
#     # Retrieve the current conversation history for the file
#     history = chat_histories.get(file_name, "")
    
#     # Generate a response using your interview model (this function should be defined/imported)
#     res = response(extracted_texts[file_name], query, history)
    
#     # Update the conversation history with the new exchange
#     chat_histories[file_name] = history + f"User: {query}\nAssistant: {res}\n"
    
#     # Convert text response to audio using Google TTS
#     tts_client = texttospeech.TextToSpeechClient()
#     synthesis_input = texttospeech.SynthesisInput(text=res)
#     voice_params = texttospeech.VoiceSelectionParams(
#          language_code="en-US",  # Use the language code from the simulation data
#         name="en-US-Chirp3-HD-Charon"
#     )
#     audio_config = texttospeech.AudioConfig(
#         audio_encoding=texttospeech.AudioEncoding.MP3
#     )
#     synthesis_response = tts_client.synthesize_speech(
#         input=synthesis_input,
#         voice=voice_params,
#         audio_config=audio_config
#     )
#     # Encode audio in base64 for JSON response
#     audio_base64 = base64.b64encode(synthesis_response.audio_content).decode("utf-8")
#     url=await upload_audio_to_cloudinary(audio_base64)
#     print(url)
    
#     return {
#         "response": res,
#         "history": chat_histories[file_name],
#         "audio": url
#     }

@router.get("/start")
async def start():
    # Define your welcome message
    welcome_message = "Hello My name is Alex I am the interviewer for you today.Lets start with the breif introduction about yourself?"
    
    # Initialize the Text-to-Speech client
    tts_client = texttospeech.TextToSpeechClient()
    
    # Set up the voice parameters and audio configuration
    voice_params = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Chirp3-HD-Charon"
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    # Prepare the synthesis input
    synthesis_input = texttospeech.SynthesisInput(text=welcome_message)
    
    # Synthesize speech from the welcome message text
    synthesis_response = tts_client.synthesize_speech(
        input=synthesis_input, 
        voice=voice_params, 
        audio_config=audio_config
    )
    
    # Encode the audio content to base64 so it can be sent in a JSON response
    audio_base64 = base64.b64encode(synthesis_response.audio_content).decode("utf-8")
    
    # Upload the audio to Cloudinary (or another storage service) to obtain a URL
    audio_url = await upload_audio_to_cloudinary(audio_base64)
    
    # Return the welcome message along with the URL to the audio
    return {"message": welcome_message, "audio": audio_url}

@router.websocket("/ws/chat")
async def websocket_interview(websocket: WebSocket):
    await websocket.accept()
    file_name = None
    ping_task = None
    
    try:
        # First message should contain file_name for identification
        init_data = await websocket.receive_json()
        file_name = init_data.get("file_name")
        
        if not file_name:
            await websocket.send_json({"error": "No file_name provided"})
            await websocket.close()
            return
            
        if file_name not in extracted_texts:
            await websocket.send_json({"error": "Extracted text for the requested file not found"})
            await websocket.close()
            return
        
        if file_name not in active_connections:
            active_connections[file_name] = []
        active_connections[file_name].append(websocket)
        
        if file_name not in chat_histories:
            chat_histories[file_name] = ""
        
        tts_client = texttospeech.TextToSpeechClient()
        voice_params = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Chirp3-HD-Charon"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        async def keepalive():
            try:
                while True:
                    await asyncio.sleep(30)  # Send ping every 30 seconds
                    await websocket.send_json({"type": "ping"})
            except Exception:
                pass
        
        ping_task = asyncio.create_task(keepalive())
        
        while True:
            # Removed the timeout parameter here.
            data = await websocket.receive_json()
            
            if data.get("type") == "pong":
                continue
                
            query = data.get("query", "")
            if not query.strip():
                continue
                
            await websocket.send_json({
                "type": "status",
                "status": "processing"
            })
            
            res = response(extracted_texts[file_name], query, chat_histories[file_name])
            chat_histories[file_name] += f"User: {query}\nAssistant: {res}\n"
            
            synthesis_input = texttospeech.SynthesisInput(text=res)
            synthesis_response = tts_client.synthesize_speech(
                input=synthesis_input, 
                voice=voice_params, 
                audio_config=audio_config
            )
            
            audio_base64 = base64.b64encode(synthesis_response.audio_content).decode("utf-8")
            audio_url = await upload_audio_to_cloudinary(audio_base64)
            
            await websocket.send_json({
                "type": "response",
                "response": res,
                "audio": audio_url
            })
            
    except asyncio.TimeoutError:
        try:
            await websocket.send_json({"error": "Connection timed out due to inactivity"})
        except:
            pass
            
    except WebSocketDisconnect:
        if file_name and file_name in active_connections and websocket in active_connections[file_name]:
            active_connections[file_name].remove(websocket)
            if not active_connections[file_name]:
                del active_connections[file_name]
                
    except Exception as e:
        error_message = f"Error: {str(e)}"
        try:
            await websocket.send_json({"error": error_message})
        except:
            pass
            
    finally:
        if ping_task:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass


@router.delete("/end_chat")
async def end_chat(file_name: str):
    # Ensure the chat history exists for the requested file
    if file_name not in chat_histories:
        raise HTTPException(status_code=404, detail="Chat history for the requested file not found.")
    
    # Convert stored chat history string into a structured conversation transcript
    conversation_history = chat_histories[file_name]
    messages = []
    lines = conversation_history.strip().split("\n")
    for i in range(0, len(lines), 2):
        if i + 1 < len(lines):
            user_line = lines[i]
            assistant_line = lines[i + 1]
            if user_line.startswith("User: ") and assistant_line.startswith("Assistant: "):
                user_text = user_line[len("User: "):].strip()
                assistant_text = assistant_line[len("Assistant: "):].strip()
                messages.append({"user": user_text, "response": assistant_text})
    
    conversation = {"messages": messages, "_id": file_name}
    
    # Generate the interview evaluation scorecard using hardcoded criteria
    result = generate_scorecard(conversation)
    
    # Clear the stored data for the file from both dictionaries
    if file_name in extracted_texts:
        del extracted_texts[file_name]
    if file_name in chat_histories:
        del chat_histories[file_name]
    
    # Return the analysis result
    return result,conversation


# --- Interview Analysis Code with Hardcoded Evaluations and Strict JSON Output ---




# Endpoint to analyze the interview conversation using hardcoded evaluation criteria
@router.post("/analyze_interview")
async def analyze_interview(file_name: str):
    if file_name not in chat_histories:
        raise HTTPException(status_code=404, detail="Chat history for the requested file not found.")
    
    # Convert stored chat history string into a structured conversation transcript
    conversation_history = chat_histories[file_name]
    messages = []
    lines = conversation_history.strip().split("\n")
    for i in range(0, len(lines), 2):
        if i + 1 < len(lines):
            user_line = lines[i]
            assistant_line = lines[i + 1]
            if user_line.startswith("User: ") and assistant_line.startswith("Assistant: "):
                user_text = user_line[len("User: "):].strip()
                assistant_text = assistant_line[len("Assistant: "):].strip()
                messages.append({"user": user_text, "response": assistant_text})
    
    conversation = {"messages": messages, "_id": file_name}
    
    # Generate the interview evaluation scorecard using hardcoded criteria
    result = generate_scorecard(conversation)
    return result