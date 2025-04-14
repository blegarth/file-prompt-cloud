from typing import Dict, Any
import os
from pathlib import Path
from src.core.processor import FileProcessor
from src.gcp.uploader import GCSUploader
from src.gcp.pubsub_client import PubSubClient

class ProcessingHandler:
    """Handles the processing of files using appropriate models."""
    
    def __init__(self):
        self.processor = FileProcessor()
        self.uploader = GCSUploader()
        self.pubsub = PubSubClient()
    
    def process(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a file based on the job data."""
        try:
            # Download the file
            local_path = Path(f"/tmp/{job_data['file_path'].split('/')[-1]}")
            self.uploader.download_file(job_data['file_path'], local_path)
            
            # Process the file
            content = self.processor.preprocess_file(str(local_path))
            
            # Clean up
            local_path.unlink()
            
            # Return result
            return {
                "job_id": job_data['job_id'],
                "status": "success",
                "content": content,
                "file_path": job_data['file_path']
            }
            
        except Exception as e:
            return {
                "job_id": job_data['job_id'],
                "status": "error",
                "error": str(e),
                "file_path": job_data['file_path']
            } 