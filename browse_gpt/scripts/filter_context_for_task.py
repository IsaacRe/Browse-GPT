import sys
import os.path
from selenium.webdriver.common.by import By
import logging

from browse_gpt.browser.chromedriver import start_driver
from browse_gpt.config import TaskExecutionConfig
from browse_gpt.cache.util import (
    EmbellishedPageContext,
    get_load_path,
    get_workdir,
    save_to_cache,
    get_parse_config_id,
    get_idx_xpath_from_ann,
    PAGE_HTML_FILENAME,
    FILTERED_CONTEXT_FILENAME,
    FILTERED_HTML_FILENAME,
)
from browse_gpt.prompt.interface import filter_context

logger = logging.getLogger(__name__)


def main(config: TaskExecutionConfig):
    page_ctx = EmbellishedPageContext.from_config(config)
    filtered_ids = filter_context(ctx=page_ctx, website=config.llm_site_id, task_description=config.task_description)
    parse_config_id = get_parse_config_id(min_class_overlap=config.min_class_overlap, min_num_matches=config.min_num_matches)
    # save filtered text context

    save_to_cache(
        "\n".join([f"{id_}:{action}" for id_, action in filtered_ids]),
        filename=FILTERED_CONTEXT_FILENAME,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        page_id=config.site_id,
        subdir=parse_config_id,
    )

    xpath_by_idx = {idx: xpath for idx, xpath in map(lambda x: get_idx_xpath_from_ann(x[0]), page_ctx.parse_annotation())}

    # load page and extract xpath
    path = get_load_path(
        filename=PAGE_HTML_FILENAME,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        page_id=config.site_id,
    )
    driver = start_driver()
    driver.get(f"file://{os.path.join(get_workdir(), path)}")

    # find elements for filtered xpaths
    filtered_context = []
    for idx, _ in filtered_ids:
        xpath = xpath_by_idx[idx]
        element = driver.find_element(by=By.XPATH, value=xpath)
        filtered_context += [element.get_attribute("outerHTML")]
    filtered_context = "\n".join(filtered_context)

    # save HTML for filtered elements
    save_to_cache(
        content=filtered_context,
        filename=FILTERED_HTML_FILENAME,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        page_id=config.site_id,
        subdir=parse_config_id,
    )


if __name__ == "__main__":
    sys.exit(main(TaskExecutionConfig.parse_args()))
