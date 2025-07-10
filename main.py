# Copyright (c) Microsoft. All rights reserved.

import asyncio
import logging
import os

from backoff import runtime
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from semantic_kernel.contents import  ChatMessageContent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.agents import AgentGroupChat, AzureAIAgent, AzureAIAgentSettings



from semantic_kernel.agents.orchestration.group_chat import (
    GroupChatOrchestration, 
    RoundRobinGroupChatManager,
)

import os, time
from typing import Optional
from azure.ai.projects.aio import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import DeepResearchTool, MessageRole, ThreadMessage

from plugins.searchPlugin import SearchPlugin
from semantic_kernel.agents import Agent, ChatCompletionAgent


from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from agents.CustomGroupChatManager import CustomRoundRobinGroupChatManager
from utils.util import agent_response_callback,streaming_agent_response_callback, get_azure_openai_service,ModelAndDeploymentName,human_response_function

## reference: 
# https://github.com/microsoft/semantic-kernel/blob/main/python/samples/getting_started_with_agents/azure_ai_agent/step3_azure_ai_agent_group_chat.py
##


TASK = """
我需要一篇关于MCP的报告。
                        1. 对MCP的语言偏好是中文
                        2. 报告需要以技术白皮书风格编写
                        3. 希望优先引用的权威来源是Anthropic
                        4. 针对应用案例部分，是偏好开放源代码项目为例
                    
        整理一份详细的技术报告，内容涵盖以下内容：

                    引言
                        Model Context Protocol的背景和发展
                        它作为function call扩展的意义及目标
                    历史背景
                        协议的起源和动机
                        其在技术发展中的定位
                        协议结构与工作原理
                        详细描述协议的架构和组件
                        数据流如何在协议中传递
                        重点解析与function call的结合方式
                    技术实现细节
                        具体的实现机制
                        使用的技术栈和关键算法
                        数据格式和传输技术
                    优势与应用案例
                        与其他协议相比的主要技术或性能优势
                        当前已知的实际应用场景
                    与其他协议的比较
                        功能、性能、兼容性等方面的对比分析
                        潜在的改进方向
                    总结与展望
                        Model Context Protocol的未来发展方向
                        潜在的技术革新与生态扩展

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


async def main():
    if AZURE_APP_INSIGHTS_CONNECTION_STRING:
        set_up_tracing()
        set_up_logging()

    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("azure_ai_agent_deep_research_by_groupChat_human_in_loop-main"):

        # Set up Azure credential and client
        credential = DefaultAzureCredential(
            exclude_workload_identity_credential=True,
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
            exclude_shared_token_cache_credential=True,
            exclude_visual_studio_code_credential=True,
            exclude_developer_cli_credential=True,
            exclude_cli_credential=False,
            exclude_interactive_browser_credential=True,
            exclude_powershell_credential=True
        )



        # connect to Azure AI Project    
        project_client = AIProjectClient(
            endpoint=os.environ["DEEP_RESEARCH_PROJECT_CONNECTION_STRING"],
            credential=credential,
        )


        # get the Bing Connection ID
        conn_id = (await project_client.connections.get(name=os.environ["DEEP_RESEARCH_BING_RESOURCE_NAME"])).id


        # Initialize a Deep Research tool with Bing Connection ID and Deep Research model deployment name
        deep_research_tool = DeepResearchTool(
            bing_grounding_connection_id=conn_id,
            deep_research_model=os.environ["DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME"],
        )

        # define the deep research agent
        deep_research_demo_agent_def = await project_client.agents.create_agent(
                model=os.environ["DEEP_RESEARCH_CHAT_MODEL_DEPLOYMENT_NAME"],
                name="deep-research-demo-agent-01",
                description="A helpful agent that assists in researching scientific & technical topics.",
                instructions="You are a helpful Agent that assists in researching scientific & technical topics.",
                tools=deep_research_tool.definitions)

        deep_research_demo_agent = AzureAIAgent(
                client=project_client,
                definition=deep_research_demo_agent_def)
        
        # define reviewer agent
        reviewer_agent_definition = await project_client.agents.create_agent(
                model=os.environ["DEEP_RESEARCH_CHAT_MODEL_DEPLOYMENT_NAME"],
                name="content-reviewer-agent",
                description="An agent that reviews content for quality and adherence to guidelines.",
                instructions='''You are an art director who has opinions about copywriting born of a love for David Ogilvy.
                                The goal is to determine if the given copy is acceptable to print.
                                If so, state that it is approved.  Do not use the word "approve" unless you are giving approval.
                                If not, provide insight on how to refine suggested copy without example.''')
        
        reviewer_agent = AzureAIAgent(
                client=project_client,
                definition=reviewer_agent_definition)
        
        group_chat_orchestration = GroupChatOrchestration(
                members=[deep_research_demo_agent,reviewer_agent],
                manager=CustomRoundRobinGroupChatManager(max_rounds=5,human_response_function=human_response_function),
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
