"""
Utility functions for Deep Research Agent.
"""
import logging
from typing import Optional

from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatMessageContent
import os
from dotenv import load_dotenv
from enum import Enum
from semantic_kernel.contents import StreamingChatMessageContent
from semantic_kernel.contents import AuthorRole, ChatHistory, ChatMessageContent, FunctionCallContent




logger = logging.getLogger(__name__)

load_dotenv()

# Global variable to track new message state for streaming
is_new_message = True


class ModelAndDeploymentName(Enum):
    """
    Enum class for model and deployment name.
    """
    O3_DEEP_RESEARCH = "o3-deep-research"
    O3 = "o3"
    O3_PRO="o3-pro"
    O3_MINI = "o3-mini"
    O4_MINI = "o4-mini"
    GPT_41 = "gpt-4.1"
    GPT_41_MINI = "gpt-4.1-mini"


def agent_response_callback(msg: ChatMessageContent) -> None:
    """Observer callback – print every agent message to stdout with improved formatting."""
    role = msg.name or "(unknown)"
    content = msg.content or ""

    # If content is empty, try to get content from items (FunctionCallContent)
    if not content and hasattr(msg, 'items') and msg.items:
        function_calls = []
        for item in msg.items:
            if hasattr(item, 'function_name'):
                function_calls.append(f"Function: {item.function_name}")
                
                # Try to get arguments from different sources
                arguments = None
                
                # Check if metadata is a dict and has 'arguments' key
                if hasattr(item, 'metadata') and isinstance(item.metadata, dict) and 'arguments' in item.metadata:
                    arguments = item.metadata['arguments']
                # Check if item has arguments attribute
                elif hasattr(item, 'arguments'):
                    arguments = item.arguments
                
                if arguments:
                    function_calls.append(f"Arguments: {arguments}")
        if function_calls:
            content = "\n".join(function_calls)

    # Log to file and console
    logger.info(f"Agent Response - {role}: {content[:100]}...")

    # Pretty print to console
    print(f"\n{'=' * 60}")
    print(f"🤖 **{role}**")
    print(f"{'=' * 60}")
    print(f"{content}")
    print(f"{'=' * 60}\n")

def streaming_agent_response_callback(message: StreamingChatMessageContent, is_final: bool) -> None:
    """Observer function to print the messages from the agents.

    Args:
        message (StreamingChatMessageContent): The streaming message content from the agent.
        is_final (bool): Indicates if this is the final part of the message.
    """
    global is_new_message
    if is_new_message:
        print(f"\n{'=' * 60}")
        print(f"🤖 **{message.name}**")
        print(f"{'=' * 60}")
        is_new_message = False
    
    content = message.content or ""
    
    # If content is empty, try to get content from items (FunctionCallContent)
    if not content and hasattr(message, 'items') and message.items:
        function_calls = []
        for item in message.items:
            if hasattr(item, 'function_name'):
                function_calls.append(f"Function: {item.function_name}")
                
                # Try to get arguments from different sources
                arguments = None
                
                # Check if metadata is a dict and has 'arguments' key
                if hasattr(item, 'metadata') and isinstance(item.metadata, dict) and 'arguments' in item.metadata:
                    arguments = item.metadata['arguments']
                # Check if item has arguments attribute
                elif hasattr(item, 'arguments'):
                    arguments = item.arguments
                
                if arguments:
                    function_calls.append(f"Arguments: {arguments}")
        if function_calls:
            content = "\n".join(function_calls)
    
    print(f"{content}", end="", flush=True)
    if is_final:
        print(f"{'=' * 60}\n")
        is_new_message = True


def get_azure_openai_service(model_and_deployment_name: Optional[ModelAndDeploymentName]=ModelAndDeploymentName.GPT_41_MINI) -> AzureChatCompletion:
    """
    Create Azure OpenAI chat completion service.

    """
    return AzureChatCompletion(
        deployment_name=model_and_deployment_name.value,
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )


def truncate_text(text: str, max_length: int = 1000) -> str:
    """
    Truncate text to specified length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        str: Truncated text
    """
    if text is None:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_search_results(results: list) -> bool:
    """
    Validate search results structure.

    Args:
        results: List of search results

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(results, list) or not results:
        return False

    required_fields = ["url", "title", "snippet"]
    for result in results:
        if not isinstance(result, dict):
            return False
        if not all(field in result for field in required_fields):
            return False

    return True


async def human_response_function(chat_history: Optional[ChatHistory]=None) -> ChatMessageContent:
    """Function to get user input."""
    user_input = input("User(You)🧑‍💻: ")
    return ChatMessageContent(role=AuthorRole.USER, content=user_input)
