import os
import re
import json
import base64
import fitz  # PyMuPDF
from fastapi import APIRouter, UploadFile, File, HTTPException,Form
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
from Functions.analyse_video import analyze_video_emotion_from_cloud_url
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
    question_count = 0  # Count the number of questions asked

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

            # Increase question counter and choose appropriate response function
            question_count += 1
            if question_count < 10:
                res = response(extracted_texts[file_name], query, chat_histories[file_name])
            else:
                res = end_response(extracted_texts[file_name], query, chat_histories[file_name])

            chat_histories[file_name] += f"User: {query}\nAssistant: {res}\n"

            synthesis_input = texttospeech.SynthesisInput(text=res)
            synthesis_response = tts_client.synthesize_speech(
                input=synthesis_input, 
                voice=voice_params, 
                audio_config=audio_config
            )

            audio_base64 = base64.b64encode(synthesis_response.audio_content).decode("utf-8")
            audio_url = await upload_audio_to_cloudinary(audio_base64)

            # Build the response message and include the finished flag on the 10th question.
            message = {
                "type": "response",
                "response": res,
                "audio": audio_url
            }
            if question_count == 10:
                message["finished"] = True

            await websocket.send_json(message)

            # If finished, break the loop so no further queries are processed.
            if question_count == 10:
                break

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
    print('the conversation history', conversation_history)
    messages = []
    lines = conversation_history.strip().split("\n")
    for i in range(0, len(lines)):
        if i + 1 < len(lines):
            user_line = lines[i]
            assistant_line = lines[i + 1]
            if user_line.startswith("User: ") and assistant_line.startswith("Assistant: "):
                user_text = user_line[len("User: "):].strip()
                assistant_text = assistant_line[len("Assistant: "):].strip()
                messages.append({"user": user_text, "response": assistant_text})
    
    conversation = {"messages": messages, "_id": file_name}
    
    # First check if we have a stored URL from the upload endpoint
    video_url = None
    if hasattr(upload_video, "video_urls") and file_name in upload_video.video_urls:
        video_url = upload_video.video_urls[file_name]
    else:
        # Fall back to checking local files
        video_uploads_dir = "video_uploads"
        if os.path.exists(video_uploads_dir) and os.path.isdir(video_uploads_dir):
            video_files = [f for f in os.listdir(video_uploads_dir) if f.startswith(f"{file_name}-interview")]
            
            if video_files:
                # Use the most recent video file if multiple exist
                latest_video = sorted(video_files, key=lambda x: os.path.getmtime(os.path.join(video_uploads_dir, x)), reverse=True)[0]
                video_url = f"/video_uploads/{latest_video}"  # Use relative URL for static files
    
    # Generate the interview evaluation scorecard using hardcoded criteria
    result = generate_scorecard(conversation)
    
    # Add video URL to the result if available
    if video_url:
        emotion_data=analyze_video_emotion_from_cloud_url(video_url)

    
    # Return the analysis result with the conversation
    return result, conversation,emotion_data


# --- Interview Analysis Code with Hardcoded Evaluations and Strict JSON Output ---




@router.post("/analyze_interview")
async def analyze_interview(file_name: str):
    if file_name not in chat_histories:
        raise HTTPException(status_code=404, detail="Chat history for the requested file not found.")
    
    # Convert stored chat history string into a structured conversation transcript
    conversation_history = chat_histories[file_name]
    print(conversation_history)
    messages = []
    # Filter out any empty lines caused by trailing newlines
    lines = [line for line in conversation_history.strip().split("\n") if line]
    
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
@router.post("/upload-video")
async def upload_video(
    file_name: str = Form(...),
    video: UploadFile = File(...)
):
    try:
        # Create directory if it doesn't exist
        video_uploads_dir = "video_uploads"
        os.makedirs(video_uploads_dir, exist_ok=True)
        
        # Save the video file locally
        file_path = os.path.join(video_uploads_dir, f"{file_name}-interview.webm")
        contents = await video.read()
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Upload to Cloudinary for storage
        try:
            upload_result = cloudinary.uploader.upload(
                file_path,
                resource_type="video",
                folder="interview_recordings",
                public_id=f"{file_name}-interview"
            )
            
            video_url = upload_result["secure_url"]
        except Exception as cloud_error:
            print(f"Cloudinary upload error: {str(cloud_error)}")
            # If Cloudinary fails, we'll still keep the local file and use a local URL
            video_url = f"http://localhost:8000/video_uploads/{file_name}-interview.webm"
            
            # Store this URL somewhere accessible to the end_chat function
            # For now, let's add it to a new dictionary
            if not hasattr(upload_video, "video_urls"):
                upload_video.video_urls = {}
            upload_video.video_urls[file_name] = video_url
            
            # Don't delete the local file if Cloudinary upload failed
            return {
                "message": "Video saved locally",
                "video_url": video_url,
                "note": "Cloudinary upload failed, using local storage"
            }
        
        # Store the URL for access by the end_chat function
        if not hasattr(upload_video, "video_urls"):
            upload_video.video_urls = {}
        upload_video.video_urls[file_name] = video_url
        
        # Clean up local file after successful upload
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return {
            "message": "Video uploaded successfully",
            "video_url": video_url
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading video: {str(e)}")
