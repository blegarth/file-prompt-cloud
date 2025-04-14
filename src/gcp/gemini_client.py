import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from PIL import Image
import re
import json
from io import BytesIO
from google.cloud import secretmanager
from google.auth import default
from google.auth.transport import requests

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with the Gemini API."""
    
    def __init__(self):
        """Initialize the Gemini client with API key from environment variable."""
        self._api_key = None
        self._model = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client with API key from environment variable."""
        try:
            # Get the API key from environment variable
            self._api_key = os.getenv('GOOGLE_API_KEY')
            if not self._api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            
            # Configure the Gemini API with the API key
            genai.configure(api_key=self._api_key)
            
            # Initialize the model
            self._model = genai.GenerativeModel('gemini-2.0-flash-lite')
            
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise
    
    def generate_content(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate content using the Gemini API.
        
        Args:
            prompt: The prompt to send to the model
            **kwargs: Additional arguments to pass to the model
            
        Returns:
            Dict containing the response from the model
        """
        try:
            if not self._model:
                raise ValueError("Gemini client not initialized")
            
            # Generate content
            response = self._model.generate_content(prompt, **kwargs)
            
            # Convert response to dictionary
            result = {
                "text": response.text,
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": part.text} for part in candidate.content.parts],
                            "role": candidate.content.role
                        },
                        "finish_reason": candidate.finish_reason,
                        "safety_ratings": [
                            {
                                "category": rating.category,
                                "probability": rating.probability
                            }
                            for rating in candidate.safety_ratings
                        ]
                    }
                    for candidate in response.candidates
                ],
                "prompt_feedback": {
                    "safety_ratings": [
                        {
                            "category": rating.category,
                            "probability": rating.probability
                        }
                        for rating in response.prompt_feedback.safety_ratings
                    ]
                } if response.prompt_feedback else None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise

    def analyze_content(self, content: str, prompt: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze content using Gemini models.
        
        Args:
            content: The content to analyze (text or base64-encoded image)
            prompt: The prompt to use for analysis
            metadata: Optional metadata about the content (e.g., file type, stats)
            
        Returns:
            Dict containing analysis results
        """
        try:
            logger.info("Starting Gemini analysis")
            logger.debug(f"Content length: {len(content)} characters")
            logger.debug(f"Prompt: {prompt}")
            
            # Handle different content types
            if metadata and metadata.get('file_type') == 'image':
                # For images, create a Part object with the base64 content
                image_part = {
                    "mime_type": f"image/{metadata['image_metadata']['format'].lower()}",
                    "data": content
                }
                # Create a list of parts for the content
                parts = [
                    {"text": f"{prompt}\n\nPlease analyze this image and provide insights:"},
                    image_part
                ]

                response = self._model.generate_content(parts)
            elif metadata and metadata.get('file_type') in ['csv', 'excel']:
                # Enhance prompt for structured data
                enhanced_prompt = f"""Analyze this structured data:

{content}

Consider the following metadata:
- File type: {metadata['file_type']}
- Statistics: {json.dumps(metadata.get('stats', {}), indent=2)}
- Sheets: {metadata.get('sheets', ['N/A'])}

{prompt}"""
                response = self._model.generate_content(enhanced_prompt)
            else:
                # For text content
                enhanced_prompt = f"{prompt}\n\nContent to analyze:\n{content}"
                response = self._model.generate_content(enhanced_prompt)
            
            logger.info("Received response from Gemini")
            
            # Get the response text
            response_text = response.text
            logger.info(f"Response text: {response_text}")
            logger.debug(f"Response text length: {len(response_text)} characters")
            
            # Get prompt feedback
            prompt_feedback = response.prompt_feedback
            logger.debug(f"Prompt feedback: {prompt_feedback}")
            
            # Get safety ratings
            safety_ratings = response.candidates[0].safety_ratings
            logger.debug(f"Safety ratings: {safety_ratings}")
            
            # Get usage metadata
            usage_metadata = response.usage_metadata
            logger.debug(f"Usage metadata: {usage_metadata}")
            
            # Prepare the analysis result
            analysis = {
                "model": self._model._model_name,
                "response": response_text,
                "prompt_feedback": {
                    "block_reason": prompt_feedback.block_reason.name if prompt_feedback.block_reason else None,
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in safety_ratings
                    ]
                },
                "usage_metadata": {
                    "prompt_token_count": usage_metadata.prompt_token_count,
                    "candidates_token_count": usage_metadata.candidates_token_count,
                    "total_token_count": usage_metadata.total_token_count
                }
            }
            
            # Add structured data insights if available
            if metadata and metadata.get('file_type') in ['csv', 'excel']:
                analysis['structured_data'] = {
                    "file_type": metadata['file_type'],
                    "stats": metadata.get('stats', {}),
                    "sheets": metadata.get('sheets', [])
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            logger.exception("Full traceback:")
            return {
                "error": str(e),
                "response": "Error analyzing content"
            }
