from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import logging
from typing import List, Tuple
import undetected_chromedriver as uc

from .cache.action import ActionSpec, ElementActionType
from .prompt.interface import describe_selection, filter_context, get_text_input_for_field
from .cache.util import get_group_context_for_page_id, update_group_description_for_page_id, get_context_for_page_id
from .cache.page import new_page
from .cache.element import add_elements, add_filtered_elements, get_filtered_elements
from .processing import extract_first_interactive_from_outer_html, is_text_input, parse_page_source, DecoratedSoup, is_interactive_element
from .config import BrowingSessionConfig
from .util import timer

logger = logging.getLogger(__name__)


def select_and_run_action(
    driver: uc.Chrome,
    config: BrowingSessionConfig,
    element_ids: List[int],
    xpaths: List[str],
) -> Tuple[int, ActionSpec, str]:  # TODO query llm for description and selection from full/summarized HTML content
    # try to execute for action for filtered xpaths
    for element_id, xpath in zip(element_ids, xpaths):
        e = driver.find_element(by=By.XPATH, value=xpath)
        try:
            interactive_e = extract_first_interactive_from_outer_html(e)
        except NoSuchElementException:
            logger.warning(f"Failed to find interactive element at xpath: {xpath}")
            continue
        input_text = None
        action_type = ElementActionType.CLICK
        if is_text_input(interactive_e):
            logger.info("Generating text field input for element...")
            with timer() as t:
                input_text = get_text_input_for_field(
                    e=interactive_e,
                    website=config.llm_site_id,
                    task_description=config.task_description,
                )
                action_type = ElementActionType.INPUT_KEYS_ENTER
            logger.info(f"Done generating text input. ({t.seconds()}s)")
        action_spec = ActionSpec(action_type=action_type, input_text=input_text)

        # run the action    
        try:
            logger.info(f"Running action: {action_spec}")
            action_spec.run(driver=driver, e=interactive_e)
            logger.info("Done.")
            return element_id, action_spec, ""
        except Exception as e:
            logger.warning(f"Failed to run action: {e}")


def get_potential_actions(
    config: BrowingSessionConfig,
    page_source: str,
    session_id: int,
    task_id: int,
    url: str,
):
    # add cache page HTML and add to db
    page_id, cached = new_page(config=config, session_id=session_id, url=url, content=page_source)

    if not cached:
        # parse page for LLM context
        elems = parse_page_source(page_source)

        # add parsed elements to db
        element_ids = add_elements(db_client=config.db_client, page_id=page_id, elements=elems)

        # TODO add same-class grouping
        # query LLM for element group decriptions TODO remove group_positions
        # group_ctx = get_group_context_for_page_id(db_client=config.db_client, page_id=page_id)
        # logger.info(f"Generating descriptions for {len(group_ctx)} same-class element groups...")
        # with timer() as t:
        #     group_element_ids, group_positions, group_descriptions = zip(*[
        #         (group_element_id, group_idx, describe_selection(group_ctx).split("\n")[0])
        #         for group_element_id, group_idx, group_ctx
        #         in group_ctx
        #     ])
        # # logger.info(f"Done generating group descriptions. ({t.seconds()}s)")

        # # update db with element group descriptions
        # update_group_description_for_page_id(
        #     db_client=config.db_client,
        #     element_ids=group_element_ids,
        #     descriptions=group_descriptions,
        # )

        # TODO add this back when we use same-class groups again
        # element_ids, page_ctx, xpaths = zip(
        #     *get_context_for_page_id(db_client=config.db_client, page_id=page_id)
        # )

        page_ctx, xpaths = zip(
            *[(e.context, e.xpath) for e in elems]
        )

        # query LLM to filter parsed content
        logger.info("Filtering parsed content...")
        with timer() as t:
            filtered_elements = filter_context(ctx=page_ctx, website=config.llm_site_id, task_description=config.task_description)
            filtered_action_descriptions = [desc for _, desc in filtered_elements]
            filtered_xpaths = [xpaths[int(ann)] for ann, _ in filtered_elements]
            filtered_element_ids = [element_ids[int(ann)] for ann, _ in filtered_elements]
            filtered_elems = [elems[int(ann)] for ann, _ in filtered_elements]
        logger.info(f"Done filtering parsed content. ({t.seconds()}s)")

        # add filtered context to db
        add_filtered_elements(db_client=config.db_client, task_id=task_id, filtered_element_ids=filtered_element_ids, filtered_descriptions=filtered_action_descriptions)

    else:
        logger.info("Retrieved page from cache.")

        # retrieve filtered elements and xpaths from cache
        filtered_elements = get_filtered_elements(
            db_client=config.db_client,
            task_id=task_id,
            page_id=page_id,
        )
        filtered_element_ids, filtered_xpaths = zip(*filtered_elements) if filtered_elements else ([], [])

    return filtered_element_ids, filtered_elements, filtered_xpaths


def get_action_metadata(
    config: BrowingSessionConfig,
    element_ids: List[int],
    elements: List[DecoratedSoup],
    xpaths: List[str]
) -> Tuple[int, str, ActionSpec]:
    # try to execute for action for filtered xpaths
    for element_id, element, xpath in zip(element_ids, elements, xpaths):
        # TODO parse to find nearest interactive element (or re-prompt)
        if not is_interactive_element(element):
            logger.warning(f"Element is not interactive: {element.tag_name}")
            continue

        input_text = None
        action_type = ElementActionType.CLICK
        if is_text_input(element):
            logger.info("Generating text field input for element...")
            with timer() as t:
                input_text = get_text_input_for_field(
                    e=element,
                    website=config.llm_site_id,
                    task_description=config.task_description,
                )
                action_type = ElementActionType.INPUT_KEYS_ENTER
            logger.info(f"Done generating text input. ({t.seconds()}s)")
        action_spec = ActionSpec(action_type=action_type, input_text=input_text)

        return element_id, xpath, action_spec

    return None, None, None
