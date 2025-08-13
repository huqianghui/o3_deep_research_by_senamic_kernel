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
why 1 +1 = 2?

"""

load_dotenv()



async def main():

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
    async with  AIProjectClient(
        endpoint=os.environ["DEEP_RESEARCH_PROJECT_CONNECTION_STRING"],
        credential=credential,
    ) as project_client:

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
