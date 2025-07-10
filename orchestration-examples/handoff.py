import asyncio
import logging
import os
import sys

from semantic_kernel.agents import Agent, ChatCompletionAgent, HandoffOrchestration, OrchestrationHandoffs
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import (
    AuthorRole,
    ChatMessageContent,
    FunctionCallContent,
    FunctionResultContent,
    StreamingChatMessageContent,
)
from semantic_kernel.functions import kernel_function


# Add parent directory to path to find plugins
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from semantic_kernel.contents import  ChatMessageContent

from agents.agent_factory import (credibility_critic, data_feeder,
                               reflection_critic, report_writer, summarizer,
                               translator, manager)

from plugins.searchPlugin import SearchPlugin

from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from agents.CustomGroupChatManager import CustomRoundRobinGroupChatManager
from utils.util import agent_response_callback,streaming_agent_response_callback, get_azure_openai_service,ModelAndDeploymentName,human_response_function

## reference: 
# https://github.com/microsoft/semantic-kernel/blob/main/python/samples/getting_started_with_agents/multi_agent_orchestration/step4b_handoff_streaming_agent_response_callback.py
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


from semantic_kernel.agents import Agent, ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion


async def main():
    if AZURE_APP_INSIGHTS_CONNECTION_STRING:
        set_up_tracing()
        set_up_logging()

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("azure_ai_agent_deep_research_by_groupChat_human_in_loop-main"):

        managerAgent = manager()
        dataFeederAgent = data_feeder() 
        credibilityCriticAgent = credibility_critic()
        summarizerAgent = summarizer()
        reportWriterAgent = report_writer()
        translatorAgent = translator()
        reflectionCriticAgent = reflection_critic()

        members = [
            managerAgent,
            dataFeederAgent,
            credibilityCriticAgent,
            summarizerAgent,
            reportWriterAgent,
            translatorAgent,
            reflectionCriticAgent
        ]

        # Define the handoff relationships between agents
        handoffs = (
            OrchestrationHandoffs()
            .add(
                source_agent=managerAgent.name,
                target_agent=dataFeederAgent.name,
                description="Transfer to this agent to start the research workflow with comprehensive web search",
            )
            .add_many(
                source_agent=dataFeederAgent.name,
                target_agents={
                    credibilityCriticAgent.name: "Transfer to this agent to analyze source credibility and coverage after initial web search",
                    summarizerAgent.name: "Transfer to this agent if search results are too large (>50 items) and need summarization before analysis",
                },
            )
            .add(
                source_agent=credibilityCriticAgent.name,
                target_agent=reportWriterAgent.name,
                description="Transfer to this agent to create structured markdown report after credibility analysis is complete",
            )
            .add(
                source_agent=reportWriterAgent.name,
                target_agent=reflectionCriticAgent.name,
                description="Transfer to this agent to evaluate report quality and provide improvement feedback",
            )
            .add(
                source_agent=summarizerAgent.name,
                target_agent=credibilityCriticAgent.name,
                description="Transfer to this agent to analyze credibility after large result sets have been summarized",
            )
            .add_many(
                source_agent=reflectionCriticAgent.name,
                target_agents={
                    reportWriterAgent.name: "Transfer back to this agent if report quality is below iteration-aware threshold and needs revision. The ReflectionCriticAgent will automatically detect iteration count from conversation history.",
                    translatorAgent.name: "Transfer to this agent if report quality is approved (≥0.80) and translation is needed",
                }
            )
        )

        handoff_orchestration = HandoffOrchestration(
            members=members,
            handoffs=handoffs,
            streaming_agent_response_callback=streaming_agent_response_callback,
            agent_response_callback=agent_response_callback,
            human_response_function=human_response_function
        )

        runtime = InProcessRuntime()
        runtime.start()

        # 3. Invoke the orchestration with a task and the runtime
        orchestration_result = await handoff_orchestration.invoke(
            task=TASK,
            runtime=runtime,
        )

        value = await orchestration_result.get()
        print(f"***** Final Result *****\n{value}")

        await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())
