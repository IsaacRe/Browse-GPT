import sys
import logging
import concurrent.futures
import json

from browse_gpt.config import BrowingSessionConfig
from browse_gpt.browser.chromedriver import start_driver, wait_until_ready
from browse_gpt.cache.session import new_session
from browse_gpt.cache.task import new_task
from browse_gpt.cache.action import new_action
from browse_gpt.agent import get_potential_actions, get_action_metadata

logger = logging.getLogger(__name__)


def main(config: BrowingSessionConfig):
    session_id, _ = new_session(db_client=config.db_client, config=config)
    task_id, _ = new_task(
        db_client=config.db_client,
        session_id=session_id,
        task_description=config.task_description,
    )

    driver = start_driver()

    # main browsing loop
    url = config.url
    while True:  
        driver.get(url)
        wait_until_ready(driver)

        filtered_ids, filtered_elems, filtered_xpaths = get_potential_actions(
            config=config,
            page_source=driver.page_source,
            session_id=session_id,
            task_id=task_id,
            url=url,
        )

        element_id, _, action_metadata = get_action_metadata(
            config=config,
            element_ids=filtered_ids,
            elements=filtered_elems,
            xpaths=filtered_xpaths,
        )

        if element_id is not None:
            new_action(db_client=config.db_client, task_id=task_id, element_id=element_id, action_spec=action_metadata)
        
        break

    return 0


if __name__ == "__main__":
    sys.exit(main(BrowingSessionConfig.parse_args()))
