# AI Customer Support Bot

## GitHub Repository
GitHub link: https://github.com/blitz-blaze7/AI-Customer-Support-Bot

## Description
This project implements an AI-based customer support chatbot developed as part of an academic assignment. The system answers common customer queries using a predefined FAQ dataset and uses a Large Language Model (LLM) for handling queries not covered by the FAQs. It also includes rule-based escalation for unsafe or unsupported requests and maintains session-based conversation history stored using SQLite.

## Features
- FAQ-based question answering
- AI-based responses for non-FAQ queries
- Rule-based escalation mechanism
- Session-based conversation tracking
- REST API backend
- Web-based user interface

## Technologies Used
- Python
- Flask
- SQLite
- Groq API (LLM)
- HTML, CSS, JavaScript

## Project Structure
```
├── app.py
├── test.html
├── faqs.json
├── requirements.txt
├── demo.gif
├── README.md
├── .gitignore
└── env.example
```


## System Overview
1. User submits a query through the web interface.
2. The system checks the query against the FAQ dataset.
3. If no FAQ matches, the query is processed by the AI model.
4. Unsafe queries trigger escalation instead of an AI response.
5. Conversation history is stored using a session identifier.

## Prompt Engineering & Logic
To ensure accurate and safe responses, the following prompts and logic were implemented:

### 1. System Prompt
This is the "master instruction" sent to the LLM (Llama 3.1) for every request to define its persona and safety boundaries:
> "You are a helpful and concise customer support assistant. If the user's request is illegal, harmful, or requires human intervention, reply EXACTLY with the token: ESCALATE_TO_AGENT"

### 2. Escalation Logic
The system uses a two-tier escalation strategy:
- **Keyword Trigger:** If the user's query contains dangerous terms (e.g., *hack, fraud, exploit, breach*), the system bypasses the AI and immediately triggers an escalation response.
- **AI-Driven Trigger:** If the LLM determines a request is harmful or out-of-scope based on the system prompt, it returns a specific token (`ESCALATE_TO_AGENT`), which the backend recognizes to trigger a human-handoff message.

### 3. Contextual Memory
The bot maintains conversation history by retrieving previous messages from an SQLite database and passing them to the LLM in the following format to ensure continuity:
- `{"role": "system", "content": system_prompt}`
- `{"role": "user", "content": previous_user_message}`
- `{"role": "assistant", "content": previous_bot_response}`

## How to Run

1. Install dependencies: pip install -r requirements.txt
2. Create a `.env` file in the project root and add: GROQ_API_KEY=your_api_key_here
3. Run the application: python app.py
4. Open your browser and go to: http://localhost:5000

## Demo
![Working Demo](demo.gif)

## Model Information
- Model Used: llama-3.1-8b-instant
- API Provider: Groq
