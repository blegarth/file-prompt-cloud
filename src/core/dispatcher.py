from typing import Dict, Any
import uuid
from src.gcp.pubsub_client import PubSubClient

class JobDispatcher:
    """Handles job creation and dispatching to Pub/Sub."""
    
    def __init__(self, pubsub_client: PubSubClient = None):
        self.pubsub = pubsub_client or PubSubClient()
    
    def create_job(self, file_path: str, prompt: str, mode: str = "auto") -> str:
        """Create and dispatch a job to Pub/Sub."""
        job_data = {
            "job_id": str(uuid.uuid4()),
            "file_path": file_path,
            "prompt": prompt,
            "mode": mode
        }
        
        # Publish the job
        self.pubsub.publish_job(job_data)
        
        return job_data["job_id"] 