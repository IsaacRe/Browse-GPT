import sys
import os.path
from bs4 import BeautifulSoup

from browse_gpt.config import ParsePageConfig
from browse_gpt.browser.chromedriver import start_driver
from browse_gpt.cache.util import (
    save_to_cache,
    get_parse_config_id,
    PAGE_HTML_FILENAME,
    PARSED_CONTEXT_FILENAME,
    INSERT_IDX_IDENTIFIER,
    ANNOTATE_IDX_IDENTIFIER,
    EXTRACTED_CONTENT_GROUP_SUBDIR,
    ElementReference,
)
from browse_gpt.processing import recurse_get_context, format_text_newline, get_decorated_elem, DecoratedSoupGroup


def main(config: ParsePageConfig):
    driver = start_driver()
    driver.get(config.url)

    # save full HTML
    save_to_cache(
        content=driver.page_source,
        page_id=config.site_id,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        filename=PAGE_HTML_FILENAME,
    )

    # parse page for LLM context
    root_elem = BeautifulSoup(driver.page_source).find()
    ds = get_decorated_elem(driver=driver, soup=root_elem, parent_xpath="/", tag=root_elem.name, tag_index=0)
    text_list, elems, elem_groups = recurse_get_context(driver=driver, ds=ds)

    # insert element idx annotations and same-class group insert identifiers
    group_idx = 0
    annotated_text = []
    for element_idx, (t, e) in enumerate(zip(text_list, elems)):
        if isinstance(e, DecoratedSoupGroup):
            ref = ElementReference(idx=element_idx, xpath=e.group_xpath).to_str()
            annotated_text += [ANNOTATE_IDX_IDENTIFIER.format(ref), INSERT_IDX_IDENTIFIER.format(group_idx)]
            group_idx += 1
        else:
            ref = ElementReference(idx=element_idx, xpath=e.xpath).to_str()
            annotated_text += [ANNOTATE_IDX_IDENTIFIER.format(ref), t]
            
    annotated_text = "\n".join(annotated_text)

    # save parsed context
    parse_config_id = get_parse_config_id(min_class_overlap=config.min_class_overlap, min_num_matches=config.min_num_matches)
    save_to_cache(
        content=annotated_text,
        filename=PARSED_CONTEXT_FILENAME,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        page_id=config.site_id,
        subdir=parse_config_id,
    )

    # save text for same-group elements
    for i, g in enumerate(elem_groups):
        annotated_text = []
        for j, e in enumerate(g.elems):
            ref = ElementReference(idx=j, xpath=e.xpath).to_str()
            annotated_text += [ANNOTATE_IDX_IDENTIFIER.format(ref), format_text_newline(e.soup.get_text())]
        annotated_text = "\n".join(annotated_text)

        save_to_cache(
            content=annotated_text,
            filename=f"{i}.txt",
            session_id=config.session_id,
            cache_dir=config.cache_dir,
            page_id=config.site_id,
            subdir=os.path.join(parse_config_id, EXTRACTED_CONTENT_GROUP_SUBDIR),
        )

    return 0


if __name__ == "__main__":
    sys.exit(main(ParsePageConfig.parse_args()))
