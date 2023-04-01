from ..cache.util import ElementGroupContext

# TODO get make scripts for prompting workflow:
# 1. Describing selection list and caching
# 2. Prompting for element interaction given full context (with selection descriptions inserted) and caching results
# 

LINK_SELECTION_DESCRIPTION_RESPONSE_PREFIX = "The choice being made is to "
LINK_SELECTION_DESCRIPTION_TEMPLATE = """Below is text extracted from links in a web page:
{context}

Describe the choice being made when selecting between these links. Make your response in the format "The choice being made is to <choice>". Limit your response to 1 sentence."""


def format_describe_selection_prompt(group_ctx: ElementGroupContext):
    return LINK_SELECTION_DESCRIPTION_TEMPLATE.format(context=group_ctx.raw_text)
