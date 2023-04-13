from typing import List, Tuple
import logging
import re

from ..cache.util import ElementGroupContext, EmbellishedPageContext, remove_xpath_from_ann, parse_annotated_content

# TODO get make scripts for prompting workflow:
# 1. Describing selection list and caching
# 2. Prompting for element interaction given full context (with selection descriptions inserted) and caching results
# 

LINK_SELECTION_DESCRIPTION_RESPONSE_SPLIT_PATTERN = """is to """

LINK_SELECTION_DESCRIPTION_TEMPLATE = """Below is text extracted from links in a web page:
{context}

Describe the choice being made when selecting between these links. Make your response in the format "The choice being made is to <choice>". Limit your response to 1 sentence."""

FILTER_ELEMENTS_FROM_CONTEXT_TEMPLATE = """Below is text extracted from HTML elements on {site}. The index of each element is shown before its text in the format `%<index%>`:
{context}

List elements from above that might be useful in completing the task "{task}" or a generalization of it. Put each output in the format `%<element index%>: action taken with this element`
"""

GENERATE_INPUT_TEXT_TEMPLATE = """Below is HTML for an input field on {site}:
```html
{context}
```

Write to input into this field in order to complete the task "{task}". Put your response in the format `input: [text input]`
"""

ELEMENT_ID_ACTION_SEPARATOR = ":"
GENERATED_INPUT_TEXT_PREFIX = "input:"

STRIP_NON_ALNUM_RE = re.compile(r"^[^0-9a-zA-Z'\"]*([0-9a-zA-Z'\"].*[0-9a-zA-Z'\"])[^0-9a-zA-Z'\"]*$")

logger = logging.getLogger(__name__)


def format_describe_selection_prompt(group_ctx: str) -> str:
    return LINK_SELECTION_DESCRIPTION_TEMPLATE.format(context=group_ctx)


def format_filter_elements_prompt(page_ctx: List[str], website: str, task_description: str) -> str:
    context = "\n".join([f"%<{i}%> {ctx}" for i, ctx in enumerate(page_ctx)])
    return FILTER_ELEMENTS_FROM_CONTEXT_TEMPLATE.format(site=website, context=context, task=task_description)


def format_generate_input_text_prompt(element_ctx: str, website: str, task_description: str) -> str:
    return GENERATE_INPUT_TEXT_TEMPLATE.format(site=website, context=element_ctx, task=task_description)


def extract_selection_description(description: str) -> str:
    split = description.split(LINK_SELECTION_DESCRIPTION_RESPONSE_SPLIT_PATTERN)
    if len(split) > 1:
        return split[1]


def extract_filtered_elements(response: str) -> List[Tuple[str, str]]:
    idx_action = []
    for ann, action_response in parse_annotated_content(response):
        try:
            action, = STRIP_NON_ALNUM_RE.findall(action_response)
        except ValueError:
            logger.warning(f"Failed to parse action from response: {action_response}")
            continue
        if not ann.isnumeric():
            logger.warning(f"LLM returned non-numeric element index: {ann}")
            continue
        idx_action += [(ann, action)]
    return idx_action


def extract_generated_input_text(response: str) -> str:
    response = response.lower()
    _, _, input_text = response.partition(GENERATED_INPUT_TEXT_PREFIX)
    try:
        input_text, = STRIP_NON_ALNUM_RE.findall(input_text)
    except (ValueError, TypeError):
        raise Exception(f"Got bad response for input text generation: {response}")
    return input_text
