from google import genai
from google.genai import types
from dotenv import load_dotenv
import time
import requests
import os
import json
import re
load_dotenv()
# Retrieve the API key and initialize the client.
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
client = genai.Client(api_key=GOOGLE_API_KEY)

def analyze_video_emotion_from_cloud_url(cloud_url):
    """
    Downloads a video from the provided cloud URL, uploads it for processing,
    polls for its processing status, and then makes an LLM inference request 
    for a detailed emotion analysis focused on interview behavior.
    
    Parameters:
        cloud_url (str): The URL to the video (e.g., from Cloudinary)
    
    Returns:
        dict: The parsed JSON response with timestamp emotions and overall analysis.
    """
    local_filename = None
    video_file = None
    
    try:
        # Determine the local filename from the URL.
        local_filename = cloud_url.split("/")[-1]
        print(f"Downloading video from {cloud_url} as {local_filename}...")
        
        # Download the video file.
        response = requests.get(cloud_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to download file from {cloud_url} (status code: {response.status_code})")
        
        with open(local_filename, 'wb') as f:
            f.write(response.content)
        print("Download complete.")
        
        # Upload the file to the Gen AI service.
        print("Uploading file...")
        video_file = client.files.upload(file=local_filename)
        print(f"Completed upload: {video_file.uri}")
        
        # Poll until the video processing is complete.
        while video_file.state.name == "PROCESSING":
            #print("Waiting for video to be processed.")
            time.sleep(10)
            video_file = client.files.get(name=video_file.name)
        
        if video_file.state.name == "FAILED":
            raise ValueError(video_file.state.name)
        print(f"Video processing complete: {video_file.uri}")
        
        # Updated prompt focused on interview-relevant emotions and behaviors
        prompt = (
            "Analyze this video as an interview. Focus on emotions and behaviors relevant to interview performance "
            "such as confidence, nervousness, engagement, attentiveness, enthusiasm, professionalism, thoughtfulness, etc. "
            "Evaluate both verbal and non-verbal cues including facial expressions, body language, eye contact, speaking pace, "
            "and voice tone.\n\n"
            
            "You must output ONLY a raw JSON object with no additional text, markdown formatting, or code block syntax. "
            "The JSON structure should be:\n\n"
            "{\n"
            "  \"timestamps\": {\n"
            "    \"0:00-0:01\": {\"emotion1\": count, \"behavior1\": count, ...},\n"
            "    \"0:00-0:02\": {\"emotion1\": count, \"behavior1\": count, ...},\n"
            "    ...\n"
            "  },\n"
            "  \"interview_strengths\": [\"strength1\", \"strength2\", ...],\n"
            "  \"areas_for_improvement\": [\"area1\", \"area2\", ...],\n"
            "  \"overall_analysis\": \"A detailed paragraph analyzing the candidate's interview performance, emotional state, "
            "key moments, and professional impression\"\n"
            "}\n\n"
            
            "For timestamps, analyze the emotions and behaviors at approximately 10-second intervals. "
            "Include interview-relevant emotions and behaviors with their frequency counts. "
            "Your response must contain nothing but valid JSON that can be directly parsed."
        )
        
        print("Making LLM inference request for interview analysis...")
        # Invoke the Gemini Flash model to perform emotion analysis with a 60-second timeout.
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[video_file, prompt],
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=60000) , # Timeout of 60 seconds,
                max_output_tokens=8000
            )
        )
        
        response_text = response.text
        
        # Clean the response to handle potential markdown code blocks
        cleaned_json_text = clean_json_response(response_text)
        
        # Print the cleaned JSON text
        print("\n--- RESPONSE JSON ---")
        print(cleaned_json_text)
        
        # Attempt to parse the response as JSON and save it to a file.
        json_filename = "interview_analysis.json"
        try:
            analysis_data = json.loads(cleaned_json_text)
            
            # Save the JSON to a file with pretty formatting
            with open(json_filename, "w") as f:
                json.dump(analysis_data, f, indent=2)
            print(f"Saved JSON analysis to {json_filename}")
            
            # Print the JSON with pretty formatting
            print("\n--- FORMATTED JSON ---")
            print(json.dumps(analysis_data, indent=2))
            
            # Print the structured analysis in a readable format
            print("\n--- TIMESTAMP ANALYSIS ---")
            for timestamp, behaviors in analysis_data.get("timestamps", {}).items():
                print(f"\n{timestamp}:")
                for behavior, count in behaviors.items():
                    print(f"  {behavior}: {count}")
            
            # Print strengths
            if "interview_strengths" in analysis_data:
                print("\n--- INTERVIEW STRENGTHS ---")
                for strength in analysis_data["interview_strengths"]:
                    print(f"  • {strength}")
                    
            # Print areas for improvement
            if "areas_for_improvement" in analysis_data:
                print("\n--- AREAS FOR IMPROVEMENT ---")
                for area in analysis_data["areas_for_improvement"]:
                    print(f"  • {area}")
            
            print("\n--- OVERALL ANALYSIS ---")
            print(analysis_data.get("overall_analysis", "No overall analysis provided"))
            
            # Cleanup all files before returning
            cleanup_files(local_filename, video_file, json_filename)
            
            # Return the successfully parsed JSON object
            return analysis_data
            
        except Exception as e:
            print("Warning: The response is not a valid JSON object. Error:", e)
            print("Original response:", response_text)
            
            # Cleanup all files before returning
            cleanup_files(local_filename, video_file, json_filename)
            
            # Return the cleaned text as fallback
            return cleaned_json_text
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        
        # Cleanup any files that might have been created before the error
        cleanup_files(local_filename, video_file)
        
        # Re-raise the exception
        raise

def cleanup_files(local_video=None, video_file=None, json_file=None):
    """
    Clean up all files created during the analysis process.
    
    Parameters:
        local_video (str): Path to the downloaded video file
        video_file: The file object from the genai client
        json_file (str): Path to the JSON output file
    """
    print("\nCleaning up files...")
    
    # Delete the local video file if it exists
    if local_video and os.path.exists(local_video):
        try:
            os.remove(local_video)
            print(f"Deleted local video file: {local_video}")
        except Exception as e:
            print(f"Failed to delete local video file: {str(e)}")
    
    # Delete the uploaded file from the service if it exists
    if video_file:
        try:
            client.files.delete(name=video_file.name)
            print(f"Deleted uploaded file from service: {video_file.uri}")
        except Exception as e:
            print(f"Failed to delete uploaded file from service: {str(e)}")
    
    # Delete the JSON file if it exists
    if json_file and os.path.exists(json_file):
        try:
            os.remove(json_file)
            print(f"Deleted JSON file: {json_file}")
        except Exception as e:
            print(f"Failed to delete JSON file: {str(e)}")
    
    print("Cleanup complete.")

def clean_json_response(text):
    """
    Clean the LLM response to extract just the JSON content,
    removing any markdown code block syntax or additional text.
    
    Parameters:
        text (str): The raw text response from the LLM
        
    Returns:
        str: Cleaned JSON text
    """
    # First, try to extract content from markdown code blocks
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    matches = re.findall(code_block_pattern, text)
    
    if matches:
        # Use the first code block found
        return matches[0].strip()
    
    # If no code blocks found, look for JSON-like content (starts with { and ends with })
    json_pattern = r"(\{[\s\S]*\})"
    matches = re.findall(json_pattern, text)
    
    if matches:
        # Use the first JSON-like content found
        return matches[0].strip()
    
    # If all else fails, return the original text with minimal cleaning
    # Remove any lines that don't look like they could be part of JSON
    lines = text.split('\n')
    filtered_lines = []
    for line in lines:
        if line.strip() and not line.strip().startswith('```') and not line.strip().startswith('#'):
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

# data=analyze_video_emotion_from_cloud_url("https://res.cloudinary.com/dh91ceeql/video/upload/v1744129657/interview_recordings/Sahil%20Kumar%20Resume%20%282024%29.pdf-interview.webm")
# print(data)