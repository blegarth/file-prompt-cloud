from google.cloud import pubsub_v1
import json
import os
from typing import Generator, Dict, Any, Set
from queue import Queue, Empty
import threading
import logging
from rich.console import Console

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

class ResultListener:
    """Listens for and processes job results from Pub/Sub."""
    
    def __init__(self, project_id: str = None, subscription_id: str = None):
        try:
            self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
            self.subscription_id = subscription_id or os.getenv('PUBSUB_RESULTS_SUBSCRIPTION', 'file-processing-results-sub')
            
            if not self.project_id:
                raise ValueError("GCP_PROJECT_ID environment variable is not set")
            if not self.subscription_id:
                raise ValueError("PUBSUB_RESULTS_SUBSCRIPTION environment variable is not set")
                
            self.subscriber = pubsub_v1.SubscriberClient()
            self.subscription_path = self.subscriber.subscription_path(
                self.project_id, self.subscription_id
            )
            self.message_queue = Queue()
            self.stop_event = threading.Event()
            self.processed_files: Set[str] = set()  # Track processed file paths
            logger.info(f"ResultListener initialized with project_id={self.project_id}, subscription_id={self.subscription_id}")
            logger.info(f"Subscription path: {self.subscription_path}")
        except Exception as e:
            logger.error(f"Error initializing ResultListener: {str(e)}")
            raise
    
    def add_file(self, file_path: str) -> None:
        """Add a file path to track.
        
        Args:
            file_path: The path of the file to track
        """
        self.processed_files.add(file_path)
        logger.info(f"Added file {file_path} to tracking. Total files: {len(self.processed_files)}")
    
    def remove_file(self, file_path: str) -> None:
        """Remove a file path from tracking.
        
        Args:
            file_path: The path of the file to remove
        """
        self.processed_files.discard(file_path)
        logger.info(f"Removed file {file_path} from tracking. Total files: {len(self.processed_files)}")
    
    def _format_result(self, data: Dict[str, Any]) -> str:
        """Format the result for display."""
        if data['status'] == 'error':
            return f"[bold red]Error:[/bold red] {data.get('error', 'Unknown error')}"
        
        content = data.get('content', 'No content')
        analysis = data.get('analysis', {})
        
        # Create a formatted string with the results
        result_parts = []
        
        # File information
        result_parts.append(
            f"[bold blue]File:[/bold blue] {data.get('file_path', 'unknown')}\n"
            f"[bold green]Status:[/bold green] {data['status']}\n"
        )
        
        # Model information if available
        if 'model' in analysis:
            result_parts.append(f"[bold cyan]Model:[/bold cyan] {analysis['model']}\n")
        
        # Main analysis content
        if content:
            result_parts.append(
                f"[bold]Analysis:[/bold]\n"
                f"{content}\n"
            )
        
        # Prompt feedback if available
        if 'prompt_feedback' in analysis:
            feedback = analysis['prompt_feedback']
            feedback_parts = []
            
            if feedback.get('block_reason'):
                feedback_parts.append(f"[bold yellow]Block Reason:[/bold yellow] {feedback['block_reason']}")
            
            if feedback.get('safety_ratings'):
                feedback_parts.append("[bold]Safety Ratings:[/bold]")
                for rating in feedback['safety_ratings']:
                    feedback_parts.append(f"  • {rating['category']}: {rating['probability']}")
            
            if feedback_parts:
                result_parts.append("\n".join(feedback_parts) + "\n")
        
        # Usage metadata if available
        if 'usage_metadata' in analysis:
            usage = analysis['usage_metadata']
            usage_parts = [
                "[bold]Token Usage:[/bold]",
                f"  • Prompt Tokens: {usage.get('prompt_token_count', 'N/A')}",
                f"  • Candidates Tokens: {usage.get('candidates_token_count', 'N/A')}",
                f"  • Total Tokens: {usage.get('total_token_count', 'N/A')}"
            ]
            
            result_parts.append("\n".join(usage_parts) + "\n")
        
        # Add a separator line between results
        return "\n" + "─" * 80 + "\n" + "".join(result_parts)
    
    def _message_callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        """Process a received message."""
        try:
            # Parse the message data
            data = json.loads(message.data.decode('utf-8'))
            
            # Format and display the result
            formatted_result = self._format_result(data)
            console.print(formatted_result)
            
            # Put the result in the queue
            self.message_queue.put(data)
            
            # Acknowledge the message
            message.ack()
            logger.info("Acknowledged message")
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding message data: {str(e)}")
            message.nack()
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            message.nack()
    
    def listen(self) -> Generator[Dict[str, Any], None, None]:
        """Listen for results from the results topic.
        
        Yields:
            Dict containing the result data
        """
        try:
            # Start the subscriber
            streaming_pull_future = self.subscriber.subscribe(
                self.subscription_path,
                callback=self._message_callback
            )
            logger.info(f"Listening for results on subscription: {self.subscription_path}")
            
            # Keep the main thread alive
            with self.subscriber:
                try:
                    # Yield results as they come in
                    while not self.stop_event.is_set():
                        try:
                            result = self.message_queue.get(timeout=1.0)
                            yield result
                        except Empty:
                            continue
                except Exception as e:
                    logger.error(f"Error in listen loop: {str(e)}")
                    raise
                finally:
                    # Cancel the subscription
                    streaming_pull_future.cancel()
                    streaming_pull_future.result()
                    
        except Exception as e:
            logger.error(f"Error in listen: {str(e)}")
            raise
    
    def stop(self) -> None:
        """Stop listening for results."""
        self.stop_event.set()
        logger.info("Stop signal received") 