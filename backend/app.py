import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Allow requests from your frontend origin (adjust if needed, '*' is insecure for production)
CORS(app)

# Simple route to check if the backend is running
@app.route('/')
def home():
    return "¡Hola! Backend is running."

# Placeholder route for generating exercises
@app.route('/generate-exercises')
def generate_exercises():
    # Get the 'n' parameter from the query string (e.g., /generate-exercises?lessons=3)
    num_lessons_str = request.args.get('lessons', default='1', type=str)

    # Basic validation (we'll improve this later)
    try:
        num_lessons = int(num_lessons_str)
        if num_lessons <= 0:
            num_lessons = 1
    except ValueError:
        return jsonify({"error": "Invalid number of lessons specified."}), 400

    print(f"Request received to generate exercises for last {num_lessons} lessons.")

    # --- LATER: This is where we will: ---
    # 1. Read the Google Doc (using GOOGLE_DOC_ID from .env)
    # 2. Parse the last 'num_lessons' lessons
    # 3. Construct a prompt for the LLM
    # 4. Call the LLM API (using GEMINI_API_KEY from .env)
    # 5. Process the LLM response
    # ---

    # For now, return dummy data
    dummy_exercises = [
        {"type": "multiple-choice", "question": "¿Qué significa 'manzana'?", "options": ["Apple", "Book", "Window"], "answer": "Apple"},
        {"type": "fill-in-blank", "question": "Yo ___ (aprender) español.", "answer": "aprendo"}
    ]

    # Add a note about which doc ID and key *would* be used (for debugging now)
    doc_id = os.getenv("GOOGLE_DOC_ID", "Not Set")
    api_key_present = "Yes" if os.getenv("GEMINI_API_KEY") else "No"


    return jsonify({
        "message": f"Placeholder: Generated exercises for last {num_lessons} lessons.",
        "doc_id_used": doc_id,
        "api_key_present": api_key_present,
        "exercises": dummy_exercises
        })

if __name__ == '__main__':
    # Debug=True allows auto-reloading when you save changes
    app.run(debug=True, port=5000) # Runs on http://127.0.0.1:5000