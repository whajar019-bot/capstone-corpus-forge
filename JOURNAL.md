# Dev Journal

## May 16, 2026

### What I did today
- Set up virtual environment
- Installed Flask, ChromaDB, PyMuPDF, google-generativeai
- Created database.py with SQLite tables for documents, artifacts and usage
- Tested database initialization successfully
- Set up GitHub repository and pushed first commit

### What I learned
- How virtual environments work in Python
- How SQLite databases are structured
- How to use git add, commit and push

### Challenges
- Understanding the setup process
- Running commands in the wrong folder multiple times

---

## May 17, 2026

### What I did today
- Created ingestor.py to extract text from PDF, text, markdown and source code files
- Tested ingestor with a markdown file successfully
- Created retriever.py using ChromaDB for document storage and semantic search
- Tested retriever with no errors

### What I learned
- How PyMuPDF reads text from PDF files
- How ChromaDB stores documents as vector embeddings
- How chunking works — splitting documents into 500 character pieces with 50 character overlap

### Challenges
- Copilot kept modifying the wrong file (retriever.py instead of ai_client.py)
- Had to delete and recreate files multiple times

---

## May 23, 2026

### What I did today
- Created ai_client.py to integrate Google Gemini AI for chat, flashcards, quiz and code review
- Created app.py connecting all modules into a Flask web server with 10 API routes
- Created templates/index.html with full UI including upload, documents, chat, flashcards, quiz, code review and usage dashboard sections
- Successfully ran the app for the first time at http://127.0.0.1:5000
- Successfully uploaded a document and saw it appear in the documents section
- Fixed Gemini model name from gemini-1.5-flash to gemini-2.0-flash
- Debugged missing templates folder and uploads folder issues

### What I learned
- How Flask routes work and how to connect frontend to backend using fetch()
- How to read Python error tracebacks to find the root cause
- How the .env file stores secret API keys safely
- How Google Gemini API works and what models are available

### Challenges
- The templates folder was a file not a directory, had to delete and recreate it
- Port 5000 kept being occupied requiring kill commands to free it
- The .env file was in the wrong folder causing API key not found errors
- Gemini model gemini-1.5-flash was deprecated, had to update to gemini-2.0-flash

---

## May 24, 2026

### What I did today
- Fixed .env file location — it was missing from capstone-corpus-forge folder
- Got a new Google API key after quota was exhausted
- Updated README.md with full setup instructions
- Updated JOURNAL.md with full development history

### What I learned
- How Google AI Studio free tier quota limits work
- That limit: 0 means the API key itself has no quota, not just daily limit
- Importance of keeping .env file in the correct project folder

### Challenges
- Google API free tier quota exhausted on first key
- New API key also had quota issues
- Had to run kill $(lsof -t -i:5000) repeatedly to free port 5000