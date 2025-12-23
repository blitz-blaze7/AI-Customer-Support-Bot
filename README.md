# AI Customer Support Bot

## Description
This project implements an AI-based customer support chatbot developed as part of an academic assignment. The system answers common customer queries using a predefined FAQ dataset and uses a Large Language Model (LLM) for handling queries not covered by the FAQs. It also includes rule-based escalation for unsafe or unsupported requests and maintains session-based conversation history.

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
    customer_support_bot/
    ├── app.py
    ├── test.html
    ├── faqs.json
    ├── requirements.txt
    ├── demo.gif
    └── README.md


## System Overview
1. User submits a query through the web interface.
2. The system checks the query against the FAQ dataset.
3. If no FAQ matches, the query is processed by the AI model.
4. Unsafe queries trigger escalation instead of an AI response.
5. Conversation history is stored using a session identifier.

## Demo
![Working Demo](demo.gif)

## Model Information
- Model Used: llama-3.1-8b-instant
- API Provider: Groq
