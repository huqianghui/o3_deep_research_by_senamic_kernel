"""
Agent factory for creating specialized research agents.
"""
import logging

from semantic_kernel.agents import ChatCompletionAgent

from plugins.searchPlugin import SearchPlugin
from utils.prompts import (CREDIBILITY_CRITIC_PROMPT, DATA_FEEDER_PROMPT,
                      REFLECTION_CRITIC_PROMPT, REPORT_WRITER_PROMPT,
                      SUMMARIZER_PROMPT, TRANSLATOR_PROMPT)
from utils import get_azure_openai_service,ModelAndDeploymentName

logger = logging.getLogger(__name__)


def data_feeder() -> ChatCompletionAgent:
    """Create data feeder agent for web search operations."""
    logger.info("Creating DataFeederAgent")
    return ChatCompletionAgent(
        name="DataFeederAgent",
        description="Performs comprehensive web search using Tavily API and returns structured JSON results.",
        instructions=DATA_FEEDER_PROMPT,
        service=get_azure_openai_service(ModelAndDeploymentName.gpt41_mini),
        plugins=[SearchPlugin()]
    )


def credibility_critic() -> ChatCompletionAgent:
    """Create credibility critic agent for source verification."""
    logger.info("Creating CredibilityCriticAgent")
    return ChatCompletionAgent(
        name="CredibilityCriticAgent",
        description="Analyzes credibility and coverage of search results using advanced LLM analysis.",
        instructions=CREDIBILITY_CRITIC_PROMPT,
        service=get_azure_openai_service(ModelAndDeploymentName.gpt41_mini),
        plugins=[SearchPlugin()]
    )


def summarizer() -> ChatCompletionAgent:
    """Create summarizer agent for result compression."""
    logger.info("Creating SummarizerAgent")
    return ChatCompletionAgent(
        name="SummarizerAgent",
        description="Synthesizes large volumes of search results into comprehensive, organized summaries.",
        instructions=SUMMARIZER_PROMPT,
        service=get_azure_openai_service(ModelAndDeploymentName.gpt41_mini)
    )


def report_writer() -> ChatCompletionAgent:
    """Create report writer agent for markdown report generation."""
    logger.info("Creating ReportWriterAgent")
    return ChatCompletionAgent(
        name="ReportWriterAgent",
        description="Creates structured markdown reports with proper citations, hyperlinks, and visual content.",
        instructions=REPORT_WRITER_PROMPT,
        service=get_azure_openai_service(ModelAndDeploymentName.o3)
    )


def translator() -> ChatCompletionAgent:
    """Create translator agent for bilingual translation."""
    logger.info("Creating TranslatorAgent")
    return ChatCompletionAgent(
        name="TranslatorAgent",
        description="Provides natural English-Chinese translation while preserving technical accuracy and formatting.",
        instructions=TRANSLATOR_PROMPT,
        service=get_azure_openai_service(ModelAndDeploymentName.gpt41)
    )


def reflection_critic() -> ChatCompletionAgent:
    """Create reflection critic agent for report quality assessment."""
    logger.info("Creating ReflectionCriticAgent")
    return ChatCompletionAgent(
        name="ReflectionCriticAgent",
        description="Evaluates report quality for coverage, coherence, citations and provides improvement feedback.",
        instructions=REFLECTION_CRITIC_PROMPT,
        service=get_azure_openai_service(ModelAndDeploymentName.o3)
    )
