"""
Tests for SegFormer HTTP Client Service

Test coverage for SegFormerClient with mocked httpx responses.
"""

import pytest
import httpx
from unittest.mock import Mock, patch, mock_open, AsyncMock
from pathlib import Path

from app.services.segformer_client import SegFormerClient


@pytest.fixture
def segformer_client():
    """Create a SegFormerClient instance for testing"""
    return SegFormerClient()


@pytest.fixture
def mock_image_path(tmp_path):
    """Create a temporary image file for testing"""
    image_file = tmp_path / "test_image.jpg"
    image_file.write_bytes(b"fake image data")
    return str(image_file)


@pytest.fixture
def mock_response_json():
    """Mock successful JSON response"""
    return {
        "analysis": {
            "defects": [],
            "status": "pass"
        }
    }


class TestSegFormerClientInitialization:
    """Test SegFormerClient initialization"""
    
    def test_init_sets_base_url(self, segformer_client):
        """Test that initialization sets base URL correctly"""
        assert segformer_client.base_url is not None
        assert not segformer_client.base_url.endswith('/')
    
    def test_init_sets_timeout(self, segformer_client):
        """Test that initialization sets timeout"""
        assert segformer_client.timeout > 0
    
    def test_init_sets_retry_config(self, segformer_client):
        """Test that initialization sets retry configuration"""
        assert segformer_client.max_retries == 3
        assert segformer_client.retry_delays == [1.0, 2.0, 4.0]


class TestInferImageSuccess:
    """Test successful image inference scenarios"""
    
    @pytest.mark.asyncio
    async def test_infer_image_success_json_response(
        self, segformer_client, mock_image_path, mock_response_json
    ):
        """Test successful inference with JSON response"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'{"analysis": {"status": "pass"}}'
        mock_response.json.return_value = mock_response_json
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context
            
            result = await segformer_client.infer_image(mock_image_path)
        
        assert result is not None
        assert 'result_json' in result
        assert 'combined_image' in result
        assert 'mask_image' in result
        assert 'overlay_image' in result
        assert result['result_json'] == mock_response_json
    
    @pytest.mark.asyncio
    async def test_infer_image_calls_correct_endpoint(
        self, segformer_client, mock_image_path
    ):
        """Test that inference calls the correct endpoint"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'{"analysis": {}}'
        mock_response.json.return_value = {"analysis": {}}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context
            
            await segformer_client.infer_image(mock_image_path)
            
            # Verify the endpoint was called
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert '/upload' in str(call_args)


class TestInferImageErrors:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_infer_image_file_not_found(self, segformer_client):
        """Test that FileNotFoundError is raised for missing file"""
        with pytest.raises(FileNotFoundError, match="Image file not found"):
            await segformer_client.infer_image("/nonexistent/path/image.jpg")
    
    @pytest.mark.asyncio
    async def test_infer_image_timeout_no_retry(self, segformer_client, mock_image_path):
        """Test timeout handling without retry exhaustion"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            mock_client.return_value = mock_context
            
            with pytest.raises(httpx.TimeoutException):
                await segformer_client.infer_image(mock_image_path)
    
    @pytest.mark.asyncio
    async def test_infer_image_connection_error(self, segformer_client, mock_image_path):
        """Test connection error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.return_value = mock_context
            
            with pytest.raises(httpx.ConnectError, match="Could not connect"):
                await segformer_client.infer_image(mock_image_path)
    
    @pytest.mark.asyncio
    async def test_infer_image_http_4xx_error_no_retry(
        self, segformer_client, mock_image_path
    ):
        """Test that 4xx errors are not retried"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "Bad Request", request=Mock(), response=mock_response
            )
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context
            
            with pytest.raises(httpx.HTTPStatusError):
                await segformer_client.infer_image(mock_image_path)
    
    @pytest.mark.asyncio
    async def test_infer_image_http_5xx_error_with_retry(
        self, segformer_client, mock_image_path
    ):
        """Test that 5xx errors are retried"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "Internal Server Error", request=Mock(), response=mock_response
            )
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context
            
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Mock sleep to speed up test
                with pytest.raises(httpx.HTTPStatusError):
                    await segformer_client.infer_image(mock_image_path)


class TestRetryLogic:
    """Test retry logic with exponential backoff"""
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout_then_success(
        self, segformer_client, mock_image_path
    ):
        """Test that retry succeeds after initial timeout"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'{"analysis": {}}'
        mock_response.json.return_value = {"analysis": {}}
        mock_response.raise_for_status = Mock()
        
        # First call times out, second succeeds
        call_count = 0
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("Timeout")
            return mock_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context
            
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await segformer_client.infer_image(mock_image_path)
                
                # Verify sleep was called for retry delay
                assert mock_sleep.called
                assert call_count == 2
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_retry_exhausted_after_3_attempts(
        self, segformer_client, mock_image_path
    ):
        """Test that retry is exhausted after max attempts"""
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(httpx.TimeoutException, match="after 3 attempts"):
                    await segformer_client.infer_image(mock_image_path)
                
                assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(
        self, segformer_client, mock_image_path
    ):
        """Test that exponential backoff uses correct delays"""
        async def mock_post(*args, **kwargs):
            raise httpx.TimeoutException("Timeout")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context
            
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                with pytest.raises(httpx.TimeoutException):
                    await segformer_client.infer_image(mock_image_path)
                
                # Verify sleep was called with correct delays (1s, 2s)
                # Note: 3rd attempt doesn't sleep
                calls = mock_sleep.call_args_list
                assert len(calls) == 2
                assert calls[0][0][0] == 1.0
                assert calls[1][0][0] == 2.0


class TestResponseParsing:
    """Test response parsing logic"""
    
    def test_parse_response_json(self, segformer_client):
        """Test parsing JSON response"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'{"test": "data"}'
        mock_response.json.return_value = {"test": "data"}
        
        result = segformer_client._parse_response(mock_response)
        
        assert result['result_json'] == {"test": "data"}
        assert result['combined_image'] == b''
        assert result['mask_image'] == b''
        assert result['overlay_image'] == b''
    
    def test_parse_response_empty_content(self, segformer_client):
        """Test that empty content raises ValueError"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b''
        
        with pytest.raises(ValueError, match="Empty response content"):
            segformer_client._parse_response(mock_response)
    
    def test_parse_response_invalid_json(self, segformer_client):
        """Test that invalid JSON raises ValueError"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'invalid json'
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            segformer_client._parse_response(mock_response)
    
    def test_parse_response_invalid_content_type(self, segformer_client):
        """Test that invalid content type raises ValueError"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.content = b'<html></html>'
        
        with pytest.raises(ValueError, match="Unexpected content type"):
            segformer_client._parse_response(mock_response)
    
    def test_parse_response_json_not_dict(self, segformer_client):
        """Test that non-dict JSON raises ValueError"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.content = b'["array", "not", "dict"]'
        mock_response.json.return_value = ["array", "not", "dict"]
        
        with pytest.raises(ValueError, match="Expected JSON object"):
            segformer_client._parse_response(mock_response)
