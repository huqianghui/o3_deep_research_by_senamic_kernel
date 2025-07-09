
import asyncio
import sys

from semantic_kernel.agents.orchestration.group_chat import BooleanResult, RoundRobinGroupChatManager
from semantic_kernel.contents import  ChatHistory
from typing_extensions import override


class CustomRoundRobinGroupChatManager(RoundRobinGroupChatManager):
    """Custom round robin group chat manager to enable user input."""

    @override
    async def should_request_user_input(self, chat_history: ChatHistory) -> BooleanResult:
        """Override the default behavior to request user input after the reviewer's message.

        The manager will check if input from human is needed after each agent message.
        """
        if len(chat_history.messages) == 0:
            return BooleanResult(
                result=False,
                reason="No agents have spoken yet.",
            )
        last_message = chat_history.messages[-1]
        if last_message.name == "Reviewer":
            return BooleanResult(
                result=True,
                reason="User input is needed after the reviewer's message.",
            )

        return BooleanResult(
            result=False,
            reason="User input is not needed if the last message is not from the reviewer.",
        )