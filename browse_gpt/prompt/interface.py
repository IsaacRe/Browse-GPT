import logging
from typing import List
from undetected_chromedriver.webelement import WebElement

from .template import format_describe_selection_prompt, extract_selection_description, format_filter_elements_prompt, extract_filtered_elements, extract_generated_input_text, format_generate_input_text_prompt
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


"""Generate text to input into an HTML input field element"""
def get_text_input_for_field(e: WebElement, website: str, task_description: str) -> str:
    outer_html = e.get_attribute("outerHTML")
    prompt = format_generate_input_text_prompt(
        element_ctx=outer_html,
        website=website,
        task_description=task_description
    )
    message = single_response(prompt)
    return extract_generated_input_text(message)
