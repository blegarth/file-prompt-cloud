import logging
from typing import Optional, Any

class Monitoring:
    def __init__(self, project_id: Optional[str] = None):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def record_processing_time(self, file_name: str, duration_ms: float) -> None:
        """Record the time taken to process a file in milliseconds."""
        self.logger.info(f"Processing time for {file_name}: {duration_ms}ms")
    
    def record_error(self, error_type: str, details: Optional[str] = None, **kwargs: Any) -> None:
        """Record an error occurrence."""
        message = f"Error occurred: {error_type}"
        if details:
            message += f" - {details}"
        self.logger.error(message)
    
    def record_file_processed(self, file_name: str, success: bool = True, **kwargs: Any) -> None:
        """Record the completion of file processing."""
        status = "successfully" if success else "with errors"
        self.logger.info(f"Completed processing of file {file_name} {status}")
    
    def record_processing_start(self, file_name: str, **kwargs: Any) -> None:
        """Record the start of file processing."""
        self.logger.info(f"Starting processing of file: {file_name}")
    
    def log_info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(message)
    
    def log_warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(message)
