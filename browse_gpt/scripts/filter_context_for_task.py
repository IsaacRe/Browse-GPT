import sys
import os.path
from selenium.webdriver.common.by import By
import logging

from browse_gpt.browser.chromedriver import start_driver
from browse_gpt.config import TaskExecutionConfig
from browse_gpt.cache.util import (
    get_load_path,
    get_workdir,
    PAGE_HTML_FILENAME,
)
from browse_gpt.cache.element import get_context_for_page
from browse_gpt.prompt.interface import filter_context
from browse_gpt.db import DBClient
from browse_gpt.model import Task, Session, FilteredElement

logger = logging.getLogger(__name__)


def main(config: TaskExecutionConfig):
    db_client = DBClient(config.db_url)

    # add task to db
    with db_client.transaction() as db_session:
        session: Session = db_session.query(Session).filter(Session.tag == config.session_id).one()
        task = Task(
            session_id=session.id,
            is_root=True,
            context=config.task_description,
        )
        db_session.add(task)
        db_session.commit()

        task_id = task.id

    element_ids, page_ctx, xpaths = zip(
        *get_context_for_page(db_client=db_client, url_hash=config.site_id)
    )

    filtered_elements = filter_context(ctx=page_ctx, website=config.llm_site_id, task_description=config.task_description)
    filtered_xpaths = [xpaths[int(ann)] for ann, _ in filtered_elements]
    filtered_element_ids = [element_ids[int(ann)] for ann, _ in filtered_elements]

    # load page and extract xpath
    path = get_load_path(
        filename=PAGE_HTML_FILENAME,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        page_id=config.site_id,
    )
    driver = start_driver()
    driver.get(f"file://{os.path.join(get_workdir(), path)}")

    # try to find elements for filtered xpaths
    for xpath in filtered_xpaths:
        driver.find_element(by=By.XPATH, value=xpath)

    # add filtered context to db
    with db_client.transaction() as db_session:
        for element_id in filtered_element_ids:
            filtered_elem = FilteredElement(
                task_id=task_id,
                element_id=element_id,
            )
            db_session.add(filtered_elem)


if __name__ == "__main__":
    sys.exit(main(TaskExecutionConfig.parse_args()))
