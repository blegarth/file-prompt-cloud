from google.cloud import pubsub_v1
import json
import uuid
import os
from typing import Dict, Any

class PubSubClient:
    """Handles Pub/Sub messaging for job processing."""
    
    def __init__(self, project_id: str = None, topic_id: str = None):
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
        self.topic_id = topic_id or os.getenv('PUBSUB_TOPIC')
        
        if not self.project_id or not self.topic_id:
            raise ValueError("GCP project ID and Pub/Sub topic must be provided or set in environment variables")
            
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
    
    def publish_job(self, job_data: Dict[str, Any]) -> str:
        """Publish a job to Pub/Sub and return the job ID."""
        # Generate a unique job ID if not provided
        if 'job_id' not in job_data:
            job_data['job_id'] = str(uuid.uuid4())
        
        # Convert job data to JSON
        data = json.dumps(job_data).encode('utf-8')
        
        # Publish the message
        future = self.publisher.publish(self.topic_path, data)
        future.result()  # Wait for the publish to complete
        
        return job_data['job_id']
    
    def create_subscription(self, subscription_id: str) -> None:
        """Create a subscription for receiving job results."""
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(
            self.project_id, subscription_id
        )
        
        # Create the subscription
        subscriber.create_subscription(
            request={
                "name": subscription_path,
                "topic": self.topic_path,
            }
        )
    
    def delete_subscription(self, subscription_id: str) -> None:
        """Delete a subscription."""
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(
            self.project_id, subscription_id
        )
        
        # Delete the subscription
        subscriber.delete_subscription(request={"subscription": subscription_path}) 