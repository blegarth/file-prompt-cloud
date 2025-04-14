import os
import json
import logging
from pathlib import Path
from typing import Dict, Any
from google.cloud import storage, pubsub_v1
from src.core.processor import FileProcessor
from src.gcp.uploader import GCSUploader
from src.gcp.gemini_client import GeminiClient
from src.core.monitoring import Monitoring

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_file(event: Dict[str, Any]) -> None:
    """Process a file using Gemini models."""
    try:
        # Initialize clients
        project_id = os.getenv('GCP_PROJECT_ID')
        bucket_name = os.getenv('GCS_BUCKET_NAME')
        
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Bucket Name: {bucket_name}")
        
        if not all([project_id, bucket_name]):
            raise ValueError("Missing required environment variables")
        
        pubsub_client = pubsub_v1.PublisherClient()
        uploader = GCSUploader(bucket_name)
        processor = FileProcessor()
        monitor = Monitoring(project_id)
        
        # Extract job data
        logger.info(f"Event: {event}")
        job_data = json.loads(event['data']['message']['data'])
        logger.info(f"Job data: {job_data}")
        file_path = job_data['file_path']
        prompt = job_data.get('prompt', 'Analyze this content and provide insights.')
        job_id = job_data.get('job_id')
        
        if not job_id:
            raise ValueError("Job ID is required")
        
        # Download file to local path
        local_path = Path('/tmp') / Path(file_path).name
        uploader.download_file(file_path, local_path)
        
        try:
            # Process file using the streamlined processor
            result = processor.preprocess_file(str(local_path), prompt=prompt)
            
            # Clean up
            local_path.unlink()
            
            # Add job metadata to result
            result['job_id'] = job_id
            result['timestamp'] = event['data']['message'].get('publishTime', '')
            
            # Enhanced logging of the result
            logger.info("=== Publishing Result to Pub/Sub ===")
            logger.info(f"Job ID: {job_id}")
            logger.info(f"File Path: {file_path}")
            logger.info(f"Result Content: {json.dumps(result, indent=2)}")
            logger.info("===================================")
            
            # Publish result to the results topic
            results_topic = os.getenv('PUBSUB_RESULTS_TOPIC', 'file-processing-results-topic')
            topic_path = pubsub_client.topic_path(project_id, results_topic)
            logger.info(f"Publishing result to topic: {results_topic}")
            
            try:
                # Publish the result
                future = pubsub_client.publish(topic_path, json.dumps(result).encode('utf-8'))
                message_id = future.result()  # Wait for the publish to complete
                logger.info(f"Successfully published message with ID: {message_id}")
            except Exception as publish_error:
                logger.error(f"Failed to publish result: {str(publish_error)}")
                raise
            
            # Log success
            monitor.record_file_processed(file_path)
            
        except Exception as e:
            # Log error
            logger.error(f"Error processing file {file_path}: {str(e)}")
            monitor.record_error(str(e))
            
            # Publish error with enhanced logging
            error_result = {
                "status": "error",
                "error": str(e),
                "file_path": file_path,
                "job_id": job_id,
                "timestamp": event['data']['message'].get('publishTime', '')
            }
            
            logger.error("=== Publishing Error Result to Pub/Sub ===")
            logger.error(f"Job ID: {job_id}")
            logger.error(f"File Path: {file_path}")
            logger.error(f"Error: {str(e)}")
            logger.error(f"Error Result: {json.dumps(error_result, indent=2)}")
            logger.error("=======================================")
            
            try:
                # Publish error to the same results topic
                results_topic = os.getenv('PUBSUB_RESULTS_TOPIC', 'file-processing-results-topic')
                topic_path = pubsub_client.topic_path(project_id, results_topic)
                future = pubsub_client.publish(topic_path, json.dumps(error_result).encode('utf-8'))
                message_id = future.result()  # Wait for the publish to complete
                logger.info(f"Successfully published error message with ID: {message_id}")
            except Exception as publish_error:
                logger.error(f"Failed to publish error result: {str(publish_error)}")
                raise
            
    except Exception as e:
        logger.error(f"Error in process_file: {str(e)}")
        raise
