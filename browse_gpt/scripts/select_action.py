import sys
import os.path
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import logging

from browse_gpt.browser.chromedriver import start_driver
from browse_gpt.config import TaskExecutionConfig
from browse_gpt.cache.util import (
    get_load_path,
    get_workdir,
    PAGE_HTML_FILENAME,
)
from browse_gpt.cache.util import get_filtered_context_for_page
from browse_gpt.cache.action import ActionSpec, ElementActionType
from browse_gpt.prompt.interface import get_text_input_for_field
from browse_gpt.db import DBClient
from browse_gpt.model import Task, Session, Page, Action
from browse_gpt.processing import extract_first_interactive_from_outer_html, is_text_input

logger = logging.getLogger(__name__)


def main(config: TaskExecutionConfig):
    db_client = DBClient(config.db_url)

    # get xpaths for filtered elements
    element_ids, filtered_xpaths = zip(*
        get_filtered_context_for_page(
            db_client=db_client,
            task_description=config.task_description,
            url_hash=config.site_id,
        )
    )

    # get task id
    with db_client.transaction() as db_session:
        session = db_session.query(Session).filter(Session.tag == config.session_id).one()
        page = db_session.query(Page).filter(Page.session_id == session.id).filter(Page.url_hash == config.site_id).one()
        task = db_session.query(Task).filter(Task.session_id == session.id).filter(Task.context == config.task_description).one()

        task_id = task.id

    # load page and extract xpath
    path = get_load_path(
        filename=PAGE_HTML_FILENAME,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        page_id=config.site_id,
    )
    driver = start_driver()
    driver.get(f"file://{os.path.join(get_workdir(), path)}")

    # try to execute for action for filtered xpaths
    for i, (element_id, xpath) in enumerate(zip(element_ids, filtered_xpaths)):
        e = driver.find_element(by=By.XPATH, value=xpath)
        try:
            interactive_e = extract_first_interactive_from_outer_html(e)
        except NoSuchElementException:
            logger.warning(f"Failed to find interactive element at xpath: {xpath}")
            continue
        input_text = None
        action_type = ElementActionType.CLICK
        if is_text_input(interactive_e):
            input_text = get_text_input_for_field(
                e=interactive_e,
                website=config.llm_site_id,
                task_description=config.task_description,
            )
            action_type = ElementActionType.INPUT_KEYS_ENTER
        action_spec = ActionSpec(action_type=action_type, input_text=input_text)

        # add action to db
        with db_client.transaction() as db_session:
            action = Action(
                task_id=task_id,
                element_id=element_id,
                action_position=i,
                metadata_=action_spec.to_json(),
            )
            db_session.add(action)

        # run the action    
        try:
            action_spec.run(driver=driver, e=interactive_e)
        except Exception as e:
            logger.warning(f"Failed to run action: {e}")


if __name__ == "__main__":
    sys.exit(main(TaskExecutionConfig.parse_args()))
