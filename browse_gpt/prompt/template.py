from typing import List, Tuple
import logging
import re

from ..cache.util import parse_annotated_content

# TODO get make scripts for prompting workflow:
# 1. Describing selection list and caching
# 2. Prompting for element interaction given full context (with selection descriptions inserted) and caching results
# 

LINK_SELECTION_DESCRIPTION_TEMPLATE = """Below is text extracted from links in a web page:
{context}

Describe the choice being made when selecting between these links. Make your response in the format "The choice being made is to [choice]". Limit your response to 1 sentence."""

FILTER_ELEMENTS_FROM_CONTEXT_TEMPLATE = """Below is text extracted from HTML elements on {site}. The index of each element is shown before its text in the format `%<index%>`:
{context}

List elements from above that might be useful in completing the task "{task}" or a generalization of it. Put each output in the format `%<element index%>: action taken with this element`
"""

ACTION_SELECTION_TEMPLATE = """Below is HTML from {site}:
```html
{page_context}
```

{task_context}

What is the next step to complete this task using the above HTML? Put your answer in the format:
```
The next step is to [next step]
Element id: [css id of the element to use]
```
"""

ACTION_SELECTION_TEMPLATE_V2 = """{task_context}
The site now shows the following HTML:
```html
{page_context}
```

What is the next step to {task}? Put your answer in the format:
```
The next step is to [next step]
Element id: [css id of the element to use]
```
"""

GENERATE_INPUT_TEXT_TEMPLATE = """Below is HTML for an input field on {site}:
```html
{context}
```

Write to input into this field in order to complete the task "{task}". Put your response in the format `input: [text input]`
"""

TASK_CONTEXT_TEMPLATE = "I'm browsing {site} in order to {task}."
ACTION_CONTEXT_TEMPLATE = """ So far I've completed the following actions:
{actions}
"""

TASK_RESPONSE_SEPARATOR = "is to "

ELEMENT_ID_ACTION_SEPARATOR = ":"

SELECTED_ACTION_PREFIX = "id:"
GENERATED_INPUT_TEXT_PREFIX = "input:"

STRIP_NON_ALNUM_RE = re.compile(r"^[^0-9a-zA-Z'\"]*([0-9a-zA-Z'\"].*[0-9a-zA-Z'\"])[^0-9a-zA-Z'\"]*$")

logger = logging.getLogger(__name__)


def format_describe_selection_prompt(group_ctx: str) -> str:
    return LINK_SELECTION_DESCRIPTION_TEMPLATE.format(context=group_ctx)


def format_filter_elements_prompt(page_ctx: List[str], website: str, task_description: str) -> str:
    context = "\n".join([f"%<{i}%> {ctx}" for i, ctx in enumerate(page_ctx)])
    return FILTER_ELEMENTS_FROM_CONTEXT_TEMPLATE.format(site=website, context=context, task=task_description)


def format_action_selection_prompt(task_ctx: "TaskContext", page_ctx: str) -> str:
    return ACTION_SELECTION_TEMPLATE.format(
        site=task_ctx.site,
        page_ctx=page_ctx,
        task_ctx=task_ctx.format(),
    )


def format_action_selection_v2_prompt(task_ctx: "TaskContext", page_ctx: str) -> str:
    return ACTION_SELECTION_TEMPLATE_V2.format(
        task_context=task_ctx.format(),
        page_context=page_ctx,
        task=task_ctx.task,
    )


def format_generate_input_text_prompt(element_ctx: str, website: str, task_description: str) -> str:
    return GENERATE_INPUT_TEXT_TEMPLATE.format(site=website, context=element_ctx, task=task_description)


def extract_selection_description(description: str) -> str:
    split = description.split(TASK_RESPONSE_SEPARATOR)
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
        idx_action += [(int(ann), action)]
    return idx_action


def extract_selected_action(response: str) -> Tuple[int, str]:
    e = Exception(f"Got bad response for task selection: {response}")
    _, _, description_element_id_response = response.lower().partition(TASK_RESPONSE_SEPARATOR)
    if not description_element_id_response:
        raise e
    description, _, element_id_response = description_element_id_response.partition("\n")
    if not element_id_response:
        raise e
    _, _, element_id = element_id_response.partition(SELECTED_ACTION_PREFIX)
    if not (element_id and element_id.isnumeric()):
        raise e
    return int(element_id), description


def extract_generated_input_text(response: str) -> str:
    response = response.lower()
    _, _, input_text = response.partition(GENERATED_INPUT_TEXT_PREFIX)
    try:
        input_text, = STRIP_NON_ALNUM_RE.findall(input_text)
    except (ValueError, TypeError):
        raise Exception(f"Got bad response for input text generation: {response}")
    return input_text


class TaskContext:
    def __init__(self, task: str, site: str, *actions: str):
        self.task = task
        self.site = site
        self.actions = list(actions)

    def _format_task(self) -> str:
        return TASK_CONTEXT_TEMPLATE.format(task=self.task, site=self.site)

    def _format_actions(self) -> str:
        if self.actions:
            return ACTION_CONTEXT_TEMPLATE.format(
                actions="\n".join([f"- {action}" for action in self.actions])
            )
        return ""

    def add_action(self, action: str):
        self.actions += [action]
    
    def format(self):
        return self._format_task() + self._format_actions()
