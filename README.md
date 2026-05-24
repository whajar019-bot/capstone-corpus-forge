# Corpus Forge

An AI-powered document knowledge platform built for the EPITA 
Generative AI for Software Engineering course (2026).

## What it does
Upload documents (PDF, text, markdown, source code) and interact 
with them using AI — ask questions, generate flashcards, quizzes, 
and code reviews.

## Setup Instructions

### 1. Clone the repository
git clone https://github.com/whajar019-bot/capstone-corpus-forge
cd capstone-corpus-forge

### 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

### 3. Install dependencies
pip install flask google-generativeai chromadb pymupdf python-dotenv

### 4. Create a .env file
Create a file called .env in the root folder and add:
GOOGLE_API_KEY=your_google_api_key_here

Get your API key at https://aistudio.google.com

### 5. Run the application
python app.py

### 6. Open in browser
Go to http://127.0.0.1:5000

## Features
- Upload PDF, text, markdown, and source code files
- Chat with your documents using AI
- Generate flashcards and quizzes
- Get AI code reviews
- Track AI usage and token count

## Team
- Yaseen Elhamali
- Wael Bahi
- Ahmad Halabi
- Walid Hajar


