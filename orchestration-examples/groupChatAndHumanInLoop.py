"""
grouupchat orchestration to implement deepresearch.
"""

import asyncio
import logging
import os
import sys

# Add parent directory to path to find plugins
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from semantic_kernel.contents import  ChatMessageContent

from semantic_kernel.agents.orchestration.group_chat import (
    GroupChatOrchestration, 
    RoundRobinGroupChatManager,
)

from plugins.searchPlugin import SearchPlugin

from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from agents.CustomGroupChatManager import CustomRoundRobinGroupChatManager
from utils.util import agent_response_callback,streaming_agent_response_callback, get_azure_openai_service,ModelAndDeploymentName,human_response_function

## reference: 
# https://github.com/microsoft/semantic-kernel/tree/main/python/samples/getting_started_with_agents/multi_agent_orchestration
##


TASK = """
我需要一篇关于大语言模型的MCP( Model Context Protocol)的报告。
"""

load_dotenv()

AZURE_APP_INSIGHTS_CONNECTION_STRING = os.getenv("AZURE_APP_INSIGHTS_CONNECTION_STRING")

resource = Resource.create({ResourceAttributes.SERVICE_NAME: "Deep Research by Semantic Kernel"})


def set_up_tracing():
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import set_tracer_provider

    # Initialize a trace provider for the application. This is a factory for creating tracers.
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(AzureMonitorTraceExporter(connection_string=AZURE_APP_INSIGHTS_CONNECTION_STRING))
    )
    # Sets the global default tracer provider
    set_tracer_provider(tracer_provider)


def set_up_logging():
    from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    # Create and set a global logger provider for the application.
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(AzureMonitorLogExporter(connection_string=AZURE_APP_INSIGHTS_CONNECTION_STRING))
    )
    # Sets the global default logger provider
    set_logger_provider(logger_provider)

    # Create a logging handler to write logging records, in OTLP format, to the exporter.
    handler = LoggingHandler()
    # Attach the handler to the root logger. `getLogger()` with no arguments returns the root logger.
    # Events from all child loggers will be processed by this handler.
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


from semantic_kernel.agents import Agent, ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

searchPlugin = SearchPlugin()

def get_agents() -> list[Agent]:
    researcher = ChatCompletionAgent(
        name="Researcher",
        description="A researcher agent.",
        plugins=[searchPlugin],
        instructions=(
            '''You are an excellent researcher and content writer. You can do deep research, collect data in the internet by tavily_search  and create new content and edit contents based on the feedback.
              And you always output the entire content in the response, not just the changes or diff.
              Do not just respond user input. 
              Always output the entire content in the response in any case.
            '''
        ),
        service=get_azure_openai_service(ModelAndDeploymentName.O3_DEEP_RESEARCH),
    )
    reviewer = ChatCompletionAgent(
        name="Reviewer",
        description="A content reviewer.",
        instructions=(
            "You are an excellent content reviewer. You review the content and provide feedback to the writer."
        ),
        service=get_azure_openai_service(ModelAndDeploymentName.GPT_41_MINI),
    )
    return [researcher, reviewer]

from semantic_kernel.contents import ChatMessageContent


from semantic_kernel.agents import GroupChatOrchestration, RoundRobinGroupChatManager


from semantic_kernel.agents.runtime import InProcessRuntime


async def main():
    if AZURE_APP_INSIGHTS_CONNECTION_STRING:
        set_up_tracing()
        set_up_logging()

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("azure_ai_agent_deep_research_by_groupChat_human_in_loop-main"):
        agents = get_agents()
        group_chat_orchestration = GroupChatOrchestration(
            members=agents,
            manager=CustomRoundRobinGroupChatManager(max_rounds=5,human_response_function=human_response_function),  # Odd number so writer gets the last word
            agent_response_callback=agent_response_callback
        )

        runtime = InProcessRuntime()
        runtime.start()

        orchestration_result = await group_chat_orchestration.invoke(
            task=TASK,
            runtime=runtime
        )

        value = await orchestration_result.get()
        print(f"***** Final Result *****\n{value}")

        await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())
