"""
SegFormer HTTP Client Service
Handles communication with external SegFormer model service
"""

import httpx
import asyncio
import logging
from typing import Dict
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)


class SegFormerClient:
    """Client for communicating with SegFormer inference service"""
    
    def __init__(self):
        """Initialize the SegFormer client with configuration"""
        self.base_url = settings.segformer_service_url.rstrip('/')
        self.timeout = settings.segformer_timeout
        self.max_retries = 3
        self.retry_delays = [1.0, 2.0, 4.0]  # Exponential backoff: 1s, 2s, 4s
    
    async def infer_image(self, image_path: str) -> dict:
        """
        Send image to SegFormer service and return analysis results with images.
        
        Implements retry logic with exponential backoff for transient failures.
        
        Args:
            image_path: Path to the image file to analyze
            
        Returns:
            Dictionary containing:
                - result_json: Analysis results as dict
                - combined_image: Combined result image as bytes
                - mask_image: Segmentation mask image as bytes
                - overlay_image: Overlay visualization image as bytes
                
        Raises:
            httpx.HTTPError: For HTTP-related errors
            httpx.TimeoutException: If request times out after all retries
            FileNotFoundError: If image_path does not exist
            ValueError: If response format is invalid
        """
        image_path_obj = Path(image_path)
        
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Retry loop with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries} to infer image: {image_path}")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    # Open and send the image file
                    with open(image_path_obj, 'rb') as f:
                        files = {'image': (image_path_obj.name, f, 'image/jpeg')}
                        response = await client.post(
                            f"{self.base_url}/upload",
                            files=files
                        )
                    
                    # Raise exception for HTTP errors
                    response.raise_for_status()
                    
                    # Parse the response
                    result = self._parse_response(response)
                    logger.info(f"Successfully inferred image: {image_path}")
                    return result
                    
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"All retry attempts exhausted for {image_path}")
                    raise httpx.TimeoutException(
                        f"Request timed out after {self.max_retries} attempts"
                    ) from e
                    
            except httpx.ConnectError as e:
                last_exception = e
                logger.error(f"Connection error on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Failed to connect to SegFormer service at {self.base_url}")
                    raise httpx.ConnectError(
                        f"Could not connect to SegFormer service at {self.base_url} after {self.max_retries} attempts"
                    ) from e
                    
            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    logger.error(f"Client error (HTTP {e.response.status_code}): {str(e)}")
                    raise
                # Retry on 5xx errors (server errors)
                else:
                    last_exception = e
                    logger.warning(f"Server error on attempt {attempt + 1}/{self.max_retries} (HTTP {e.response.status_code}): {str(e)}")
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        logger.info(f"Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Server error persisted after {self.max_retries} attempts")
                        raise
                        
            except httpx.HTTPError as e:
                # Generic HTTP error
                last_exception = e
                logger.error(f"HTTP error on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"HTTP error persisted after {self.max_retries} attempts")
                    raise
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
    
    def _parse_response(self, response: httpx.Response) -> dict:
        """
        Parse the HTTP response from SegFormer service.
        
        Args:
            response: The HTTP response object
            
        Returns:
            Parsed dictionary with result_json and image bytes
            
        Raises:
            ValueError: If response format is invalid or missing required fields
        """
        content_type = response.headers.get('content-type', '')
        
        # Validate response is not empty
        if not response.content:
            raise ValueError("Empty response content received from SegFormer service")
        
        # Handle JSON response
        if 'application/json' in content_type:
            try:
                result_json = response.json()
            except Exception as e:
                raise ValueError(f"Failed to parse JSON response: {str(e)}") from e
            
            # Validate JSON structure
            if not isinstance(result_json, dict):
                raise ValueError(f"Expected JSON object, got {type(result_json).__name__}")
            
            # For simple JSON responses, return with empty images
            return {
                'result_json': result_json,
                'combined_image': b'',
                'mask_image': b'',
                'overlay_image': b''
            }
        
        # Handle multipart response with JSON and images
        elif 'multipart/form-data' in content_type:
            return self._parse_multipart_response(response)
        
        else:
            raise ValueError(f"Unexpected content type: {content_type}")
    
    def _parse_multipart_response(self, response: httpx.Response) -> dict:
        """
        Parse multipart response containing JSON and image files.
        
        Args:
            response: The HTTP response object with multipart content
            
        Returns:
            Parsed dictionary with result_json and image bytes
            
        Raises:
            ValueError: If required fields are missing
        """
        # Parse multipart content
        # Note: This is a simplified implementation assuming the service
        # returns files in a specific format. Actual implementation may vary.
        
        content = response.content
        
        # Validate content
        if not content:
            raise ValueError("Empty multipart response content")
        
        # Extract JSON from response (assuming it's embedded in the response)
        # This is a placeholder - actual parsing depends on service response format
        result_json = {}
        try:
            result_json = response.json()
        except Exception as e:
            logger.warning(f"Could not parse JSON from multipart response: {str(e)}")
            # Continue with empty dict if JSON parsing fails
        
        # Validate we have some meaningful data
        if not result_json and len(content) == 0:
            raise ValueError("No valid data found in multipart response")
        
        return {
            'result_json': result_json,
            'combined_image': content,  # Placeholder - needs proper multipart parsing
            'mask_image': b'',
            'overlay_image': b''
        }
