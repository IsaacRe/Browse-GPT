from .template import format_describe_selection_prompt, LINK_SELECTION_DESCRIPTION_RESPONSE_PREFIX
from ..llm.openai_api import single_response
from ..cache.util import ElementGroupContext


"""Describe the choice being made by selecting between elements in a group.
Output will be reinserted into full page context afterward."""
def describe_selection(group_ctx: ElementGroupContext) -> str:
    prompt = format_describe_selection_prompt(group_ctx=group_ctx)
    message = single_response(prompt)
    return message.split(LINK_SELECTION_DESCRIPTION_RESPONSE_PREFIX)[-1]
