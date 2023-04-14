import sys
import logging

from browse_gpt.db import DBClient
from browse_gpt.config import BrowingSessionConfig
from browse_gpt.browser.chromedriver import start_driver
from browse_gpt.processing import get_current_page_context
from browse_gpt.prompt.interface import describe_selection, filter_context
from browse_gpt.cache.util import get_group_context_for_page_id, update_group_description_for_page_id, get_context_for_page_id
from browse_gpt.cache.session import new_session
from browse_gpt.cache.page import new_page
from browse_gpt.cache.element import add_elements, add_filtered_elements, get_filtered_elements
from browse_gpt.cache.task import new_task
from browse_gpt.cache.action import new_action
from browse_gpt.util import timer
from browse_gpt.agent import select_and_run_action

logger = logging.getLogger(__name__)

# TODO
# - add task branching
#   - update action object with new_page_id
#   - 
#       1. describe prior action
#       2. add to list of actions taken
#       3. maybe add another selection step after filtering
#   - break task context into combination of past action context and task context
# - add querying for external information
# - add html context branching
#    - intially just for same-class groups
# - checking for cache presence at intermediate steps (page caching completeness)
# - remove is_visible check to save time on initial HTML processing
# - query for final task selection
# - optimize DB exchanges


def main(config: BrowingSessionConfig):
    db_client = DBClient(config.db_url)

    session_id, _ = new_session(db_client=db_client, config=config)
    task_id, _ = new_task(
        db_client=db_client,
        session_id=session_id,
        task_description=config.task_description,
    )

    driver = start_driver()

    # main browsing loop
    url = config.url
    while True:

        driver.get(url)
        
        # add cache page HTML and add to db
        page_id, cached = new_page(db_client=db_client, session_id=session_id, url=url, content=driver.page_source, config=config)

        if not cached:
            # parse page for LLM context
            elems = get_current_page_context(driver)

            # add parsed elements to db
            element_ids = add_elements(db_client=db_client, page_id=page_id, elements=elems)

            # get query LLM for element group decriptions TODO remove group_positions
            group_ctx = get_group_context_for_page_id(db_client=db_client, page_id=page_id)
            logger.info(f"Generating descriptions for {len(group_ctx)} same-class element groups...")
            with timer() as t:
                group_element_ids, group_positions, group_descriptions = zip(*[
                    (group_element_id, group_idx, describe_selection(group_ctx).split("\n")[0])
                    for group_element_id, group_idx, group_ctx
                    in group_ctx
                ])
            logger.info(f"Done generating group descriptions. ({t.seconds()}s)")

            # update db with element group descriptions
            update_group_description_for_page_id(
                db_client=db_client,
                element_ids=group_element_ids,
                descriptions=group_descriptions,
            )

            # get page context TODO do we need to redefine element_ids here
            element_ids, page_ctx, xpaths = zip(
                *get_context_for_page_id(db_client=db_client, page_id=page_id)
            )

            # query LLM to filter parsed content
            logger.info("Filtering parsed content...")
            with timer() as t:
                filtered_elements = filter_context(ctx=page_ctx, website=config.llm_site_id, task_description=config.task_description)
                filtered_action_descriptions = [desc for _, desc in filtered_elements]
                filtered_xpaths = [xpaths[int(ann)] for ann, _ in filtered_elements]
                filtered_element_ids = [element_ids[int(ann)] for ann, _ in filtered_elements]
            logger.info(f"Done filtering parsed content. ({t.seconds()}s)")

            # add filtered context to db
            add_filtered_elements(db_client=db_client, task_id=task_id, filtered_element_ids=filtered_element_ids, filtered_descriptions=filtered_action_descriptions)
        
        else:
            logger.info("Retrieved page from cache.")

            # retrieve filtered elements and xpaths from cache
            filtered_elements = get_filtered_elements(
                db_client=db_client,
                task_id=task_id,
                page_id=page_id,
            )
            filtered_element_ids, filtered_xpaths = zip(*filtered_elements) if filtered_elements else ([], [])

        # attempt to interact with filtered elements
        try:
            element_id, action_spec = select_and_run_action(
                driver=driver,
                config=config,
                element_ids=filtered_element_ids, 
                xpaths=filtered_xpaths,
            )
        except TypeError:
            raise Exception("Failed to execute interact successfully with any filtered elements")

        new_action(db_client=db_client, task_id=task_id, element_id=element_id, action_spec=action_spec)
        break

    return 0


if __name__ == "__main__":
    sys.exit(main(BrowingSessionConfig.parse_args()))
