import base64
import json
import os
import traceback
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from cloudevents.http import from_http
from src.core.main import process_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('file-processing-worker')

app = Flask(__name__)

def load_env_variables():
    """Load and validate required environment variables."""
    required_vars = [
        'GCP_PROJECT_ID',
        'PUBSUB_TOPIC',
        'PUBSUB_SUBSCRIPTION',
        'GOOGLE_API_KEY_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
            logger.error(f"Missing required environment variable: {var}")
    
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    logger.info("All required environment variables are present")

# Load environment variables before anything else
try:
    load_env_variables()
except EnvironmentError as e:
    logger.error(f"Environment configuration error: {str(e)}")
    # Don't exit here, let the application start and fail fast if needed

@app.route('/pubsub', methods=['POST'])
def pubsub_handler():
    """Handle Pub/Sub push messages."""
    try:
        # Log request receipt
        logger.debug("Received Pub/Sub push request")
        
        # Debug: print the raw request
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request body: {request.data.decode('utf-8') if request.data else 'Empty'}")
        
        # Get the push message
        envelope = request.get_json()
        if not envelope:
            logger.error("No Pub/Sub message received in request")
            return jsonify(success=False, error='No Pub/Sub message received'), 400

        # Extract the message 
        if not isinstance(envelope, dict) or 'message' not in envelope:
            logger.error(f"Invalid Pub/Sub message format: {envelope}")
            return jsonify(success=False, error='Invalid Pub/Sub message format'), 400

        # Debug: log the envelope
        logger.debug(f"Envelope structure: {json.dumps(envelope, indent=2)}")
        
        # Extract the message data
        pubsub_message = envelope['message']
        
        # Check for the data field which contains the base64-encoded message
        if 'data' not in pubsub_message:
            logger.error("Missing data field in Pub/Sub message")
            return jsonify(success=False, error='Missing data field in Pub/Sub message'), 400
            
        # Decode the base64 data
        try:
            message_data_str = base64.b64decode(pubsub_message['data']).decode('utf-8')
            logger.info(f"Decoded message data: {message_data_str}")
            
            message_data = json.loads(message_data_str)
            logger.info(f"Parsed message data: {message_data}")
            
            # Validate required fields
            if 'file_path' not in message_data:
                logger.error("Message missing 'file_path' field")
                return jsonify(success=False, error="Message missing 'file_path' field"), 400

        except Exception as e:
            logger.error(f"Error decoding or parsing message data: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify(success=False, error=f"Error processing message data: {str(e)}"), 400
        
        # Create a CloudEvent
        attributes = {
            'type': 'google.cloud.pubsub.topic.publish',
            'source': f"//pubsub.googleapis.com/projects/{os.environ.get('GCP_PROJECT_ID')}/topics/{os.environ.get('PUBSUB_TOPIC')}",
        }
        
        # Create a proper cloud event with the decoded data
        cloud_event = {
            'id': pubsub_message.get('messageId', ''),
            'source': attributes['source'],
            'type': attributes['type'],
            'data': {
                'message': {
                    'data': message_data_str,
                    'messageId': pubsub_message.get('messageId', ''),
                    'publishTime': pubsub_message.get('publishTime', '')
                },
                'subscription': f"projects/{os.environ.get('GCP_PROJECT_ID')}/subscriptions/{os.environ.get('PUBSUB_SUBSCRIPTION')}"
            }
        }
        
        logger.info(f"Processing file: {message_data['file_path']}")
        
        try:
            # Process the message
            process_file(cloud_event)
            
            # Log success
            logger.info(f"Successfully processed file: {message_data['file_path']}")
            
            # Acknowledge the message by returning a success response
            return jsonify(success=True, message=f"Successfully processed file: {message_data['file_path']}"), 200
        except Exception as e:
            logger.error(f"Error in process_file: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify(success=False, error=f"Processing error: {str(e)}"), 500
        
    except Exception as e:
        # Log the detailed error with traceback
        logger.error(f"Unhandled exception in pubsub_handler: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify(success=False, error=f"Server error: {str(e)}"), 500

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint."""
    logger.info("Health check request received")
    return jsonify(status='healthy'), 200

if __name__ == '__main__':
    # Get the port from the environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Starting Flask server on port {port}")
    
    # Run the app on the specified port
    app.run(host='0.0.0.0', port=port, debug=False)

