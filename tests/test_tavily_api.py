#!/usr/bin/env python3
"""
Tavily API operation test script
Check API status and verify what kind of responses are returned.
"""

import os
import sys
from dotenv import load_dotenv
from tavily import TavilyClient

# Load environment variables
load_dotenv()

def test_tavily_api():
    """Test basic operation of Tavily API"""
    
    # Check API key
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("❌ TAVILY_API_KEY environment variable is not set")
        return False
        
    print(f"✅ API Key: {api_key[:10]}...")
    
    try:
        # Initialize Tavily client
        client = TavilyClient(api_key=api_key)
        print("✅ Tavily client initialized")
        
        # Simple search test
        print("\n🔍 Running basic search test...")
        test_queries = [
            "Python programming",
            "AI technology trends",  # General AI technology query
            "Microsoft Azure"
        ]
        
        for query in test_queries:
            print(f"\n📝 Search query: '{query}'")
            try:
                # Basic search
                response = client.search(
                    query=query,
                    max_results=3,
                    search_depth="basic",
                    include_answer=False,
                    include_raw_content=False
                )
                
                if response and "results" in response:
                    results = response["results"]
                    print(f"✅ Found {len(results)} results")
                    for i, result in enumerate(results):
                        print(f"  {i+1}. {result.get('title', 'No title')[:50]}...")
                        print(f"     URL: {result.get('url', 'No URL')}")
                        if result.get('content'):
                            print(f"     Content: {result['content'][:100]}...")
                        
                        # Check raw_content if available
                        if 'raw_content' in result:
                            if result['raw_content'] is None:
                                print(f"    ⚠️  raw_content is None!")
                            else:
                                print(f"    raw_content length: {len(result['raw_content'])}")
                        
                else:
                    print("❌ No results or invalid response format")
                    
            except Exception as e:
                print(f"❌ Search error: {str(e)}")
                
        # Test search with raw_content
        print(f"\n🔍 Search test with raw_content...")
        try:
            response = client.search(
                query="Python programming",
                max_results=2,
                search_depth="basic",
                include_answer=False,
                include_raw_content=True  # Enable raw_content
            )
            
            if response and "results" in response:
                results = response["results"]
                print(f"✅ Found {len(results)} results with raw_content")
                for result in results:
                    print(f"  Title: {result.get('title', 'No title')[:50]}...")
                    if 'raw_content' in result and result['raw_content']:
                        print(f"  Raw content length: {len(result['raw_content'])}")
                    else:
                        print("  No raw_content available")
            else:
                print("❌ No results with raw_content")
                
        except Exception as e:
            print(f"❌ Search error with raw_content: {str(e)}")
        
        print(f"\n✅ Tavily API test completed")
        return True
        
    except Exception as e:
        print(f"❌ Tavily API connection error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 Tavily API Operation Test")
    print("=" * 50)
    
    success = test_tavily_api()
    
    if success:
        print(f"\n🎉 Test completed: Tavily API is working normally")
        sys.exit(0)
    else:
        print(f"\n💥 Test failed: There is an issue with Tavily API")
        sys.exit(1)
