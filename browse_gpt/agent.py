from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import logging
from typing import List, Tuple
import undetected_chromedriver as uc

from .cache.action import ActionSpec, ElementActionType
from .prompt.interface import get_text_input_for_field
from .processing import extract_first_interactive_from_outer_html, is_text_input
from .config import BrowingSessionConfig

logger = logging.getLogger(__name__)


def select_and_run_action(
    driver: uc.Chrome,
    config: BrowingSessionConfig,
    element_ids: List[int],
    xpaths: List[str],
) -> Tuple[int, ActionSpec]:
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
            logger.info("Getting text field input for element...")
            input_text = get_text_input_for_field(
                e=interactive_e,
                website=config.llm_site_id,
                task_description=config.task_description,
            )
            action_type = ElementActionType.INPUT_KEYS_ENTER
            logger.info("Done.")
        action_spec = ActionSpec(action_type=action_type, input_text=input_text)

        # run the action    
        try:
            logger.info(f"Running action: {action_spec}")
            action_spec.run(driver=driver, e=interactive_e)
            logger.info("Done.")
            return element_id, action_spec
        except Exception as e:
            logger.warning(f"Failed to run action: {e}")
