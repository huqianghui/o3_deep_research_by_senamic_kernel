"""
Unit tests for SearchPlugin functionality.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins.searchPlugin import SearchPlugin

from dotenv import load_dotenv
load_dotenv()


class TestSearchPlugin:
    """Test cases for SearchPlugin class."""
    
    @pytest.fixture
    def plugin(self):
        """Create SearchPlugin instance for testing."""
        with patch('plugins.searchPlugin.TavilyClient') as mock_client:
            mock_client.return_value = Mock()
            return SearchPlugin()
    
    def test_plugin_initialization(self, plugin):
        """Test SearchPlugin initialization."""
        assert plugin.client is not None
        assert hasattr(plugin, 'tavily_search')

    @patch('plugins.searchPlugin.TavilyClient')
    def test_successful_search(self, mock_tavily_client):
        """Test successful search operation."""
        # Mock response
        mock_response = {
            'results': [
                {
                    'url': 'https://example.com/article1',
                    'title': 'Test Article 1',
                    'content': 'This is test content for article 1.',
                    'score': 0.85,
                    'published_date': '2025-06-01'
                },
                {
                    'url': 'https://example2.com/article2',
                    'title': 'Test Article 2',
                    'content': 'This is test content for article 2.',
                    'score': 0.78,
                    'published_date': '2025-06-02'
                }
            ]
        }
        
        # Configure mock
        mock_client_instance = Mock()
        mock_client_instance.search.return_value = mock_response
        mock_tavily_client.return_value = mock_client_instance
        
        # Create plugin and perform search
        plugin = SearchPlugin()
        result = plugin.tavily_search("test query")
        
        # Parse and validate result
        parsed_result = json.loads(result)
        assert isinstance(parsed_result, list)
        assert len(parsed_result) == 2
        assert parsed_result[0]['url'] == 'https://example.com/article1'
        assert parsed_result[0]['title'] == 'Test Article 1'
        assert 'domain' in parsed_result[0]
        assert 'crawled_at' in parsed_result[0]

    @patch('plugins.searchPlugin.TavilyClient')
    def test_search_with_images(self, mock_tavily_client):
        """Test search with image descriptions."""
        # Mock response with images
        mock_response = {
            'results': [
                {
                    'url': 'https://example.com/article1',
                    'title': 'Test Article 1',
                    'content': 'This is test content.',
                    'score': 0.85
                }
            ],
            'images': [
                {
                    'url': 'https://example.com/image1.jpg',
                    'description': 'Test image description'
                },
                {
                    'url': 'https://example.com/image2.png',
                    'description': 'Another test image'
                }
            ]
        }
        
        mock_client_instance = Mock()
        mock_client_instance.search.return_value = mock_response
        mock_tavily_client.return_value = mock_client_instance
        
        plugin = SearchPlugin()
        result = plugin.tavily_search("test query", include_image_descriptions=True)
        
        parsed_result = json.loads(result)
        assert len(parsed_result) == 1
        assert 'images' in parsed_result[0]
        assert len(parsed_result[0]['images']) == 2
        assert parsed_result[0]['images'][0]['url'] == 'https://example.com/image1.jpg'

    @patch('plugins.searchPlugin.TavilyClient')
    def test_search_error_handling(self, mock_tavily_client):
        """Test error handling in search operation."""
        # Configure mock to raise exception
        mock_client_instance = Mock()
        mock_client_instance.search.side_effect = Exception("API Error")
        mock_tavily_client.return_value = mock_client_instance
        
        plugin = SearchPlugin()
        result = plugin.tavily_search("test query")
        
        parsed_result = json.loads(result)
        assert isinstance(parsed_result, list)
        assert len(parsed_result) == 1
        assert 'error' in parsed_result[0]
        assert 'API Error' in parsed_result[0]['error']
    
    def test_build_search_params(self, plugin):
        """Test search parameter building."""
        params = plugin._build_search_params(
            query="test query",
            top_k=10,
            time_range="week",
            topic="news",
            search_depth="advanced",
            include_image_descriptions=True
        )
        
        assert params['query'] == "test query"
        assert params['max_results'] == 10
        assert params['time_range'] == "week"
        assert params['topic'] == "news"
        assert params['search_depth'] == "advanced"
        assert params['include_image_descriptions'] is True
    
    def test_domain_extraction(self, plugin):
        """Test domain extraction from URLs."""
        test_cases = [
            ("https://www.example.com/article", "www.example.com"),
            ("http://news.bbc.co.uk/story", "news.bbc.co.uk"),
            ("https://reuters.com", "reuters.com"),
            ("", ""),
            ("invalid-url", "")
        ]
        
        for url, expected_domain in test_cases:
            domain = plugin._extract_domain(url)
            assert domain == expected_domain

    @patch('plugins.searchPlugin.TavilyClient')
    def test_tavily_search_time_range_default(self, mock_tavily_client):
        plugin = SearchPlugin()
        class DummyClient:
            def search(self, **kwargs):
                # Return search parameters for testing
                return {"results": [{"url": "https://example.com", "title": "title", "content": "text", "score": 1.0}]}
        plugin.client = DummyClient()
        # Call with time_range=None
        result_json = plugin.tavily_search("test query", top_k=5, time_range=None)
        assert '"title": "title"' in result_json
        # Test if time_range="month" parameter is generated correctly by testing _build_search_params directly
        params = plugin._build_search_params("test", 5, None, "general", "basic", False)
        assert "time_range" not in params  # None should not be included
        params2 = plugin._build_search_params("test", 5, "month", "general", "basic", False)
        assert params2["time_range"] == "month"

    @patch('plugins.searchPlugin.TavilyClient')
    def test_tavily_search_none_results(self, mock_tavily_client):
        plugin = SearchPlugin()
        class NoneClient:
            def search(self, **kwargs):
                return {"results": None}
        plugin.client = NoneClient()
        # Even if None is returned, no error occurs and an empty list is returned
        result_json = plugin.tavily_search("test query", top_k=5, time_range=None)
        assert '"error"' not in result_json
        assert '[]' in result_json  # Empty list is returned

    @patch('plugins.searchPlugin.TavilyClient')
    def test_tavily_search_invalid_response(self, mock_tavily_client):
        plugin = SearchPlugin()
        class InvalidClient:
            def search(self, **kwargs):
                return "not a dict"
        plugin.client = InvalidClient()
        # Error message is returned even for invalid responses
        result_json = plugin.tavily_search("test query", top_k=5, time_range=None)
        assert '"error"' in result_json

    @patch('plugins.searchPlugin.TavilyClient')
    def test_tavily_search_integration(self, mock_tavily_client):
        """
        Integration test for SearchPlugin.tavily_search.
        - with/without time_range
        - with/without include_image_descriptions
        - whether API responses are processed correctly        
        """
        called_params = {}
        
        # Dummy client
        class DummyClient:
            def search(self, **kwargs):
                called_params.clear()
                called_params.update(kwargs)
                # When images are included
                if kwargs.get("include_images"):
                    return {
                        "results": [
                            {"url": "https://example.com", "title": "title", "content": "text", "score": 1.0}
                        ],
                        "images": [
                            {"url": "https://img.com/1.png", "description": "desc1"},
                            {"url": "https://img.com/2.png", "description": "desc2"}
                        ]
                    }
                # Without images
                return {
                    "results": [
                        {"url": "https://example.com", "title": "title", "content": "text", "score": 1.0}
                    ]
                }
                return {
                    "results": [
                        {"url": "https://example.com", "title": "title", "content": "text", "score": 1.0}
                    ]
                }
        plugin = SearchPlugin()
        plugin.client = DummyClient()

        # With time_range and images
        result_json = plugin.tavily_search(
            "integration test query", top_k=3, time_range="week", include_image_descriptions=True
        )
        assert called_params["time_range"] == "week"
        assert called_params["include_images"] is True
        assert '"images": [' in result_json
        assert '"description": "desc1"' in result_json        # Without time_range and images
        result_json2 = plugin.tavily_search(
            "integration test query", top_k=2, time_range=None, include_image_descriptions=False
        )
        assert "time_range" not in called_params
        assert "include_images" not in called_params or called_params["include_images"] is False
        assert '"images": [' not in result_json2
        assert '"title": "title"' in result_json2


class TestSearchPluginIntegration:
    """Integration tests for SearchPlugin."""
    
    @pytest.mark.integration
    @patch.dict(os.environ, {'TAVILY_API_KEY': 'test-key'})
    def test_real_search_simulation(self):
        """Test search with simulated real API response."""
        # This would test with actual API if TAVILY_API_KEY is real
        # For now, it's a placeholder for integration testing        pass
    
    @pytest.mark.integration
    def test_tavily_search_real_api(self):
        """
        Integration test using actual Tavily API.
        Only executed when TAVILY_API_KEY is available.
        """
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key or api_key == "test-key":
            pytest.skip("Skipping because TAVILY_API_KEY is not set")
        plugin = SearchPlugin()
        # Without images
        result_json = plugin.tavily_search("AI technology trends", top_k=3, time_range=None, include_image_descriptions=False)
        results = None
        try:
            results = json.loads(result_json)
        except Exception:
            pytest.fail("Unable to parse result as JSON")
        assert isinstance(results, list)
        if results and isinstance(results[0], dict):
            assert "url" in results[0]
            assert "title" in results[0]
            assert "snippet" in results[0]
        # With images
        result_json2 = plugin.tavily_search("AI technology trends", top_k=3, time_range=None, include_image_descriptions=True)
        results2 = json.loads(result_json2)
        assert isinstance(results2, list)
        # If image information is included, there should be an "images" field
        if results2 and isinstance(results2[0], dict):
            if "images" in results2[0]:
                assert isinstance(results2[0]["images"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])