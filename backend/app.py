import os
import math
import json # Import json library for parsing LLM response
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.generativeai as genai # Import Gemini library

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/documents.readonly']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
DOCUMENT_ID = os.getenv('GOOGLE_DOC_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # Load Gemini API Key
# --- End Configuration ---

# --- Configure Gemini ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")
# --- End Configuration ---


def read_paragraph_element(element):
    """Returns the text in the given ParagraphElement."""
    text_run = element.get('textRun')
    if not text_run:
        return ''
    content = text_run.get('content')
    return content if content else ''

def get_doc_content(doc_id, creds, num_lessons):
    """Uses the Docs API to retrieve the content of the FIRST 'num_lessons' lessons."""
    # (Keep the existing get_doc_content function exactly as it was in the previous step)
    # ... (Code for reading doc, finding headings, extracting relevant_text) ...
    # Make sure it returns {"title": ..., "text": relevant_text.strip()} on success
    # Or {"error": ..., "status_code": ...} on failure
    try:
        service = build('docs', 'v1', credentials=creds)
        document = service.documents().get(documentId=doc_id).execute()
        print(f"Successfully retrieved document: {document.get('title')}")

        doc_content = document.get('body').get('content', [])
        if not doc_content:
            return {"title": document.get('title'), "text": ""}

        headings = []
        paragraphs = []
        for value in doc_content:
            if 'paragraph' in value:
                p = value.get('paragraph')
                elements = p.get('elements')
                if elements:
                    paragraph_start_index = value.get('startIndex')
                    current_paragraph_text = "".join(read_paragraph_element(e) for e in elements)
                    style = p.get('paragraphStyle', {}).get('namedStyleType', '')
                    if style.startswith('HEADING'):
                        headings.append({'text': current_paragraph_text.strip(), 'startIndex': paragraph_start_index})
                    paragraphs.append({'text': current_paragraph_text, 'startIndex': paragraph_start_index})

        headings.sort(key=lambda x: x['startIndex'])

        lesson_start_index = 0
        lesson_end_index = math.inf
        doc_end_index = doc_content[-1].get('endIndex')
        if doc_end_index:
             lesson_end_index = doc_end_index

        if headings:
            lesson_start_index = headings[0]['startIndex']
            if num_lessons < len(headings):
                lesson_end_index = headings[num_lessons]['startIndex']
        else:
             lesson_start_index = 0

        print(f"Targeting content from index {lesson_start_index} to {lesson_end_index}")

        relevant_text = ""
        for p in paragraphs:
            if lesson_start_index <= p['startIndex'] < lesson_end_index:
                relevant_text += p['text']

        print(f"Total length of extracted relevant text: {len(relevant_text.strip())}")
        return {"title": document.get('title'), "text": relevant_text.strip()}

    except HttpError as err:
        # ... (keep existing HttpError handling) ...
        print(f"An API error occurred: {err}")
        error_details = f"Google Docs API Error: {err.resp.status} - {err.reason}"
        if err.resp.status == 403:
            error_details += ". Permission denied. Check Doc sharing/API enabled."
        elif err.resp.status == 404:
            error_details += ". Document not found. Check GOOGLE_DOC_ID."
        return {"error": error_details, "status_code": err.resp.status}
    except Exception as e:
        # ... (keep existing generic Exception handling) ...
        print(f"An unexpected error occurred in get_doc_content: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"An unexpected error during doc processing: {str(e)}", "status_code": 500}


@app.route('/')
def home():
    return "¡Hola! Backend is running and connected to Google Docs." # Updated message

@app.route('/generate-exercises')
def generate_exercises():
    # --- Get num_lessons (keep existing code) ---
    num_lessons_str = request.args.get('lessons', default='1', type=str)
    try:
        num_lessons = int(num_lessons_str)
        if num_lessons <= 0:
            num_lessons = 1
    except ValueError:
        return jsonify({"error": "Invalid number of lessons specified."}), 400
    print(f"Request received for FIRST {num_lessons} lessons (most recent).")

    # --- Authenticate and get document content (keep existing code) ---
    if not SERVICE_ACCOUNT_FILE or not DOCUMENT_ID:
        # ... (keep existing checks) ...
        missing = []
        if not SERVICE_ACCOUNT_FILE: missing.append("Service account credentials path")
        if not DOCUMENT_ID: missing.append("Google Doc ID")
        return jsonify({"error": f"Missing environment variables: {', '.join(missing)}"}), 500
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    except FileNotFoundError:
         return jsonify({"error": f"Service account key file not found: {SERVICE_ACCOUNT_FILE}"}), 500
    except Exception as e:
         return jsonify({"error": f"Error loading credentials: {str(e)}"}), 500

    doc_data = get_doc_content(DOCUMENT_ID, creds, num_lessons)

    if "error" in doc_data:
        status_code = doc_data.get("status_code", 500)
        return jsonify({"error": doc_data["error"]}), status_code

    extracted_text = doc_data['text']
    doc_title = doc_data['title']

    if not extracted_text.strip():
         return jsonify({"message": f"Successfully read document '{doc_title}' but no text content found for the first {num_lessons} lessons."}), 200


    # --- ** NEW: Call Gemini API ** ---
    print(f"Sending text (length: {len(extracted_text)}) to Gemini API...")

    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not configured."}), 500

    try:
        # Choose a model (gemini-pro is standard, gemini-1.5-flash is faster/cheaper)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # --- ** Prompt Engineering ** ---
        # This is crucial. Adjust it based on your needs.
        # Asking for JSON is key for easy parsing.
        prompt = f"""
        Based on the following Spanish lesson notes (vocabulary, grammar, examples) extracted from a Google Doc titled '{doc_title}':

        --- START NOTES ---
        {extracted_text}
        --- END NOTES ---

        Please generate exactly 5 Spanish practice exercises directly related to this content. Include a mix of exercise types if possible (e.g., multiple-choice, fill-in-the-blank).

        Format the output STRICTLY as a JSON list of objects. Each object should represent one exercise and must have the following keys:
        - "type": A string indicating the exercise type (e.g., "multiple-choice", "fill-in-blank").
        - "question": A string containing the question or instruction.
        - "options": A list of strings containing the choices (ONLY for "multiple-choice" type, otherwise null or omit).
        - "answer": A string containing the correct answer.

        Example JSON object for multiple-choice:
        {{"type": "multiple-choice", "question": "What is 'libro' in English?", "options": ["Book", "Table", "Chair"], "answer": "Book"}}

        Example JSON object for fill-in-blank:
        {{"type": "fill-in-blank", "question": "Yo ___ (comer) manzanas.", "options": null, "answer": "como"}}

        Return ONLY the JSON list, nothing else before or after it.
        """

        # Call the Gemini API
        response = model.generate_content(prompt)

        # Attempt to parse the response as JSON
        print("Gemini Response Text Received (Attempting JSON parse):")
        # print(response.text) # Optional: print raw response for debugging

        try:
            # Check if response has text part before accessing
            if hasattr(response, 'text'):
                # Clean potential markdown ```json ... ``` wrapper if present
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("```json"):
                     cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                     cleaned_text = cleaned_text[:-3]

                exercises = json.loads(cleaned_text) # Parse the cleaned text as JSON
                print("Successfully parsed Gemini response as JSON.")

                # Basic validation if it's a list
                if not isinstance(exercises, list):
                    raise ValueError("LLM response was valid JSON but not a list.")

                return jsonify({
                    "message": f"Successfully generated exercises from '{doc_title}' (Lessons: {num_lessons})",
                    "exercises": exercises # Return the parsed list of exercises
                })

            else:
                 # Handle cases where the response might be blocked or empty
                 print("Gemini response did not contain text. Parts:", response.parts)
                 # Check for safety ratings or finish reason if available
                 safety_info = ""
                 if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                      safety_info = f" Blocked Reason: {response.prompt_feedback.block_reason}."
                 return jsonify({"error": f"Gemini response was empty or potentially blocked.{safety_info}"}), 500


        except json.JSONDecodeError as json_err:
            print(f"Error: Failed to parse Gemini response as JSON: {json_err}")
            print("Raw Gemini Response Text was:")
            print(response.text if hasattr(response, 'text') else "[No Text Received]")
            return jsonify({"error": "Failed to parse exercise data from AI response. The AI might not have returned valid JSON.", "raw_response": response.text if hasattr(response, 'text') else None}), 500
        except ValueError as val_err:
            print(f"Error: Gemini response JSON was not a list: {val_err}")
            return jsonify({"error": f"AI response was valid JSON but not the expected format (list). {val_err}", "raw_response": cleaned_text}), 500


    except Exception as e:
        print(f"An error occurred calling Gemini API: {e}")
        # Check for specific API errors if the library provides them, otherwise generic
        # Example: Handle potential API key errors, rate limits, etc.
        # from google.api_core import exceptions as google_exceptions
        # if isinstance(e, google_exceptions.PermissionDenied):
        #     return jsonify({"error": "Gemini API Permission Denied. Check your API key."}), 403

        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred while generating exercises: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(port=5000)