# Healthcare Voice AI Agent

This project is a real-time Voice AI agent built for healthcare applications. It allows users to stream audio from a microphone via WebSockets to a backend server, which transcribes the audio using Deepgram.

## Architecture

*   **Backend:** FastAPI application handling WebSocket connections, integrating with Deepgram for real-time speech-to-text, and using Redis for memory/caching and PostgreSQL for persistent storage. Containerized using Docker.
*   **Frontend:** A lightweight vanilla HTML/JS client to record microphone audio and stream it to the backend via WebSockets.

## Tech Stack

*   **Language:** Python 3.11, JavaScript (Vanilla)
*   **Frameworks/Libraries:**
    *   FastAPI, Uvicorn (Backend API & WebSockets)
    *   Deepgram SDK (Speech-to-Text)
    *   Redis (Caching / PubSub)
    *   PostgreSQL + SQLAlchemy + asyncpg (Database)
    *   Pydantic (Data validation)
*   **Infrastructure:** Docker, Docker Compose

## Prerequisites

*   Docker and Docker Compose
*   A Deepgram API Key (Sign up at [Deepgram](https://deepgram.com/))

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in the `backend/` directory (or update the existing one) with your Deepgram API key:

```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

### 2. Running the Backend (with Docker)

The easiest way to run the backend and its dependencies (Postgres, Redis) is using Docker Compose.

```bash
cd backend
docker-compose up --build
```

This will start:
*   The FastAPI backend on `http://localhost:8000`
*   Redis on `localhost:6379`
*   PostgreSQL on `localhost:5432`

### 3. Running the Frontend

The frontend is a simple HTML file. You can open it directly in your browser, or serve it using a simple HTTP server to avoid CORS issues.

Using Python's built-in HTTP server:

```bash
cd frontend
python -m http.server 8080
```

Then navigate to `http://localhost:8080` in your web browser.

## How to Use

1.  Open the frontend application in your browser.
2.  Click **Connect WebSocket** to establish a connection with the FastAPI backend. You should see the status change to "Connected".
3.  Click **Start Recording** and allow microphone access.
4.  Speak into your microphone. You will see partial transcripts appear in real-time, followed by final transcripts as you complete your sentences.

## Assumptions & Notes

*   The current frontend uses vanilla JS and `MediaRecorder` to stream `.webm` (Opus) audio chunks.
*   The backend expects the `.env` file to be present for the Deepgram API key.
*   CORS is currently configured to allow all origins (`*`) in the backend for development purposes. This should be restricted in a production environment.
*   The application uses a random `session_id` for each WebSocket connection to track individual sessions.

## Project Structure

*   `/backend` - Contains the FastAPI application, Dockerfile, and docker-compose configuration.
    *   `/app/api` - API routes and WebSocket endpoints.
    *   `/app/core` - Configuration, logging, and core services like Redis setup.
    *   `/app/voice` - Deepgram integration and audio processing logic.
*   `/frontend` - Contains the vanilla JS client (`index.html` and `app.js`).
