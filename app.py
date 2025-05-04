"""
WhatsApp Webhook Server for Epigen Chatbot

This server receives webhook events from WhatsApp via Green API,
processes them using Google's Gemini AI model, and sends responses
back to the user.

The server is built with Flask and runs on Uvicorn for improved performance.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
import requests
from flask import Flask, request, jsonify
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
# This has no effect in production where environment variables are set differently
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# ==================== CONFIGURATION ====================

# Get API credentials from environment variables
# These will be set as secrets in Hugging Face Spaces or other cloud environments
GREEN_API_ID = os.environ.get("GREEN_API_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Check if required environment variables are set
if not GREEN_API_ID or not GREEN_API_TOKEN:
    logger.warning("WhatsApp API credentials not set. Webhook will not be able to send messages.")

if not GOOGLE_API_KEY:
    logger.warning("Google API key not set. AI responses will not work.")

# Configure logging
logger.add("webhook.log", rotation="500 MB", level="INFO", retention="10 days")

# ==================== DATA STORAGE ====================

# In-memory storage for chat histories
# In a production environment, this would be replaced with a database
whatsapp_chat_histories: Dict[str, List[Dict[str, str]]] = {}

# Knowledge base content - replace with your actual content from the Streamlit app
knowledge_content = """
# Datos de Epigen
- WhatsApp: 5544918977
- Direccion: Avenida de los Insurgentes 601, 03810 Col. Nápoles, CDMX, CP:03100
- Sitio Web: https://epigen.mx/
"""  # Add your full knowledge base here

# ==================== ROUTE HANDLERS ====================

@app.route('/', methods=['GET'])
def home():
    """
    Home route to confirm the server is running.
    
    This endpoint is useful for:
    1. Checking if the server is alive
    2. Basic health monitoring
    3. Browser-based verification
    
    Returns:
        JSON response with status message
    """
    return jsonify({
        "status": "online",
        "message": "Epigen WhatsApp webhook server is running",
        "version": "1.0.0"
    }), 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    Main webhook endpoint for WhatsApp.
    
    Handles two types of requests:
    - GET: Used by Green API to verify the webhook URL
    - POST: Receives incoming message notifications
    
    Returns:
        JSON response indicating success or error
    """
    # Handle webhook verification (GET request)
    if request.method == 'GET':
        logger.info("Received webhook verification request")
        return jsonify({"status": "webhook is active"}), 200
    
    # Handle incoming webhook events (POST request)
    try:
        # Get the JSON data from the request
        data = request.get_json()
        logger.info(f"Received webhook data: {json.dumps(data)}")
        
        # Process incoming messages
        if data.get("typeWebhook") == "incomingMessageReceived":
            message_data = data.get("messageData", {})
            
            # Handle text messages
            if message_data.get("typeMessage") == "textMessage":
                sender = data["senderData"]["sender"].split("@")[0]  # Get phone number
                message_text = message_data["textMessageData"]["textMessage"]
                logger.info(f"Received message from {sender}: {message_text}")
                
                # Process the message and get a response
                ai_response = process_message(sender, message_text)
                
                # Send the response back to the user
                send_whatsapp_message(sender, ai_response)
                
            # Handle voice messages (future enhancement)
            elif message_data.get("typeMessage") == "audioMessage":
                sender = data["senderData"]["sender"].split("@")[0]
                logger.info(f"Received audio message from {sender}")
                
                # Currently we don't process audio, so just send a default response
                send_whatsapp_message(
                    sender, 
                    "Recibí tu mensaje de voz, pero actualmente solo puedo procesar mensajes de texto."
                )
        
        return jsonify({"status": "message processed"}), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==================== MESSAGE PROCESSING ====================

def process_message(sender: str, message_text: str) -> str:
    """
    Process a message and generate an AI response.
    
    This function:
    1. Initializes chat history for new users
    2. Adds the user message to history
    3. Generates an AI response
    4. Adds the response to history
    
    Args:
        sender (str): The phone number of the sender
        message_text (str): The content of the message
        
    Returns:
        str: The AI-generated response
    """
    try:
        # Initialize chat history for new users
        if sender not in whatsapp_chat_histories:
            whatsapp_chat_histories[sender] = [
                {"role": "assistant", "content": "¡Hola! Soy el asistente de Epigen. ¿Cómo puedo ayudarte hoy? 🧬"}
            ]
            logger.info(f"Initialized new chat history for {sender}")
        
        # Add user message to history
        whatsapp_chat_histories[sender].append({"role": "user", "content": message_text})
        
        # Generate AI response with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Generate response using AI
                response = generate_ai_response(
                    whatsapp_chat_histories[sender], 
                    message_text
                )
                
                # Add AI response to history
                whatsapp_chat_histories[sender].append({"role": "assistant", "content": response})
                logger.info(f"Generated response for {sender}: {response[:50]}...")
                
                return response
            
            except Exception as e:
                logger.error(f"Attempt {attempt+1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    raise
                time.sleep(1)  # Wait before retrying
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return "Lo siento, tuve un problema procesando tu mensaje. Por favor intenta de nuevo."

def generate_ai_response(chat_history: List[Dict[str, str]], user_message: str) -> str:
    """
    Generate a response using the Google Gemini model.
    
    This function:
    1. Configures the Gemini API
    2. Formats the conversation history
    3. Adds the system message with knowledge base
    4. Generates and returns the response
    
    Args:
        chat_history (List[Dict[str, str]]): The conversation history
        user_message (str): The latest user message
        
    Returns:
        str: The generated AI response
    """
    # Import the Gemini API library
    # We import here to avoid loading it unless needed
    import google.generativeai as genai
    
    # Configure the Gemini API
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Set up the model with appropriate parameters
    generation_config = {
        "temperature": 0.7,        # Controls randomness (0.0 = deterministic, 1.0 = creative)
        "top_p": 0.95,             # Nucleus sampling parameter
        "top_k": 0,                # Limits vocabulary to top K tokens
        "max_output_tokens": 1000, # Maximum length of response
    }
    
    # Safety settings to prevent harmful or inappropriate content
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    
    # Initialize the generative model
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",  # Using the more efficient model for faster responses
        generation_config=generation_config,
        safety_settings=safety_settings,
    )
    
    # Format the conversation history for Gemini
    # Gemini uses "user" and "model" roles instead of "user" and "assistant"
    formatted_history = []
    for message in chat_history:
        role = "user" if message["role"] == "user" else "model"
        formatted_history.append({"role": role, "parts": [message["content"]]})
    
    # Add system message with knowledge base
    # This provides context about Epigen to inform the AI's responses
    system_message = (
        "Eres un agente conversacional de IA experto en epigenética y en los productos de Epigen. "
        "Usa la siguiente información para responder preguntas sobre Epigen:\n\n" + knowledge_content
    )
    formatted_history.insert(0, {"role": "model", "parts": [system_message]})
    
    # Generate response
    chat = model.start_chat(history=formatted_history)
    response = chat.send_message(user_message)
    
    return response.text

# ==================== WHATSAPP INTEGRATION ====================

def send_whatsapp_message(recipient: str, message: str) -> Optional[Dict[str, Any]]:
    """
    Send a message back to the user via WhatsApp.
    
    Uses Green API to send messages to WhatsApp users.
    
    Args:
        recipient (str): The phone number to send the message to
        message (str): The content of the message
        
    Returns:
        Optional[Dict[str, Any]]: The response from the Green API, or None if failed
    """
    # Construct the URL for the Green API endpoint
    url = f"https://api.green-api.com/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
    
    # Prepare the payload with the recipient and message
    payload = {
        "chatId": f"{recipient}@c.us",  # Format required by WhatsApp
        "message": message
    }
    
    try:
        # Send the request to Green API
        response = requests.post(url, json=payload)
        response_data = response.json()
        
        # Log the result
        if response.status_code == 200 and response_data.get("idMessage"):
            logger.info(f"Message sent to {recipient}: {message[:50]}...")
        else:
            logger.error(f"Error sending message: {response_data}")
        
        return response_data
    
    except Exception as e:
        logger.error(f"Exception when sending message: {str(e)}")
        return None

# ==================== UTILITY ROUTES ====================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring services.
    
    Returns detailed information about the server's status,
    including environment configuration and service availability.
    
    Returns:
        JSON response with health information
    """
    # Check Green API connectivity
    green_api_status = "configured" if GREEN_API_ID and GREEN_API_TOKEN else "not configured"
    
    # Check Google API connectivity
    google_api_status = "configured" if GOOGLE_API_KEY else "not configured"
    
    # Return comprehensive health status
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "green_api": green_api_status,
            "google_ai": google_api_status
        },
        "active_chats": len(whatsapp_chat_histories)
    }), 200

# ==================== SERVER STARTUP ====================

# This block only runs when executing this file directly
# In production, Uvicorn will import and run the Flask app object
if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 7860))
    
    # Log the server startup
    logger.info(f"Starting server on port {port}")
    
    # Run the server using Uvicorn
    # Using WSGI interface since Flask is a WSGI application
    uvicorn.run("app:app", host="0.0.0.0", port=port, interface="wsgi")
