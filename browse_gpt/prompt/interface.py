import logging
from typing import List, Union
from undetected_chromedriver.webelement import WebElement

from .template import format_describe_selection_prompt, extract_selection_description, format_filter_elements_prompt, extract_filtered_elements, extract_generated_input_text, format_generate_input_text_prompt, TaskContext
from ..llm.openai_api import single_response
from ..processing import DecoratedSoupGroup, DecoratedSoup

logger = logging.getLogger(__name__)


"""Describe the choice being made by selecting between elements in a group.
Output will be reinserted into full page context afterward."""
def describe_selection(group_ctx: str) -> str:
    prompt = format_describe_selection_prompt(group_ctx=group_ctx)
    message = single_response(prompt)
    return extract_selection_description(message)


"""Select an element to interact with given its extracted text.
Returns identifier corresponding to the selected context"""
def filter_context(ctx: List[str], website: str, task_description: str) -> List[str]:
    prompt = format_filter_elements_prompt(page_ctx=ctx, website=website, task_description=task_description)
    message = single_response(prompt)
    return extract_filtered_elements(message)


"""Select an action from abbreviated HTML context.
Returns the integer id of the selected element and a description of the action taken"""
def select_action(dsg: DecoratedSoupGroup, task_ctx: TaskContext) -> List[DecoratedSoup]:
    pass # TODO start here


"""Generate text to input into an HTML input field element"""
def get_text_input_for_field(e: Union[DecoratedSoup, WebElement], website: str, task_description: str) -> str:
    if isinstance(e, DecoratedSoup):
        outer_html = str(e)
    else:
        outer_html = e.get_attribute("outerHTML")
    prompt = format_generate_input_text_prompt(
        element_ctx=outer_html,
        website=website,
        task_description=task_description,
    )
    message = single_response(prompt)
    return extract_generated_input_text(message)
