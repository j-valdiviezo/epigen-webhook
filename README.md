# Epigen WhatsApp Webhook

A webhook server for the Epigen WhatsApp integration. This service processes incoming WhatsApp messages using Google's Gemini AI model and responds with information about Epigen products and services.

## Features

- Processes incoming WhatsApp messages via Green API
- Generates AI responses using Google's Gemini model
- Maintains conversation history for personalized interactions
- Provides health check and monitoring endpoints

## Technical Stack

- **Flask**: Web framework for handling HTTP requests
- **Uvicorn**: ASGI server for running the Flask application
- **Google Generative AI**: AI model for generating responses
- **Green API**: WhatsApp integration provider

## Deployment

This application is designed to be deployed as a Docker container and is compatible with:
- Hugging Face Spaces
- AWS Elastic Beanstalk
- Google Cloud Run
- Any Docker-compatible cloud platform

## Local Development

1. Clone the repository
2. Create a `.env` file with the required API keys
3. Install dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`

## Environment Variables

- `GREEN_API_ID`: Your Green API instance ID
- `GREEN_API_TOKEN`: Your Green API API token
- `GOOGLE_API_KEY`: Your Google API key for Gemini access
- `PORT`: The port to run the server on (default: 7860)

## API Endpoints

- `GET /`: Home page showing server status
- `GET /health`: Health check endpoint
- `GET/POST /webhook`: Main webhook endpoint for WhatsApp integration
