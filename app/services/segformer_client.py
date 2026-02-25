"""
SegFormer HTTP Client Service
Handles communication with external SegFormer model service
"""

import httpx
from typing import Dict
from pathlib import Path
from app.config import settings


class SegFormerClient:
    """Client for communicating with SegFormer inference service"""
    
    def __init__(self):
        """Initialize the SegFormer client with configuration"""
        self.base_url = settings.segformer_service_url.rstrip('/')
        self.timeout = settings.segformer_timeout
    
    async def infer_image(self, image_path: str) -> dict:
        """
        Send image to SegFormer service and return analysis results with images.
        
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
            FileNotFoundError: If image_path does not exist
            ValueError: If response format is invalid
        """
        image_path_obj = Path(image_path)
        
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
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
            return self._parse_response(response)
    
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
        
        # Handle JSON response
        if 'application/json' in content_type:
            result_json = response.json()
            
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
        
        # For now, return the raw content and let the caller handle it
        # This is the basic implementation for Stream A
        content = response.content
        
        # Simple validation
        if not content:
            raise ValueError("Empty response content")
        
        # Extract JSON from response (assuming it's embedded in the response)
        # This is a placeholder - actual parsing depends on service response format
        result_json = {}
        try:
            result_json = response.json()
        except Exception:
            # If JSON parsing fails, use empty dict
            pass
        
        return {
            'result_json': result_json,
            'combined_image': content,  # Placeholder - needs proper multipart parsing
            'mask_image': b'',
            'overlay_image': b''
        }
