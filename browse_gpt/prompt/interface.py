import logging
from typing import List

from .template import format_describe_selection_prompt, extract_selection_description, format_filter_elements_prompt, extract_filtered_elements
from ..llm.openai_api import single_response
from ..cache.util import ElementGroupContext, EmbellishedPageContext

logger = logging.getLogger(__name__)


"""Describe the choice being made by selecting between elements in a group.
Output will be reinserted into full page context afterward."""
def describe_selection(group_ctx: ElementGroupContext) -> str:
    prompt = format_describe_selection_prompt(group_ctx=group_ctx)
    message = single_response(prompt)
    return extract_selection_description(message)


"""Select an element to interact with given its extracted text
Returns identifier corresponding to the selected context"""
def filter_context(ctx: EmbellishedPageContext, website: str, task_description: str) -> List[str]:
    prompt = format_filter_elements_prompt(page_ctx=ctx, website=website, task_description=task_description)
    message = single_response(prompt)
    return extract_filtered_elements(message)
