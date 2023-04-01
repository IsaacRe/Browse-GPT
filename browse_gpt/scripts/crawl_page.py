import sys
import os.path
from bs4 import BeautifulSoup

from browse_gpt.config import ParsePageConfig
from browse_gpt.browser.chromedriver import start_driver
from browse_gpt.cache.util import (
    save_to_path,
    PAGE_CONTENT_FILENAME,
    PARSED_CONTEXT_FILENAME,
    INSERT_IDX_IDENTIFIER,
    ANNOTATE_IDX_IDENTIFIER,
    CLOSE_ANNOTATE_IDX_IDENTIFIER,
    EXTRACTED_CONTENT_GROUP_SUBDIR,
    ElementReference,
)
from browse_gpt.processing import recurse_get_context, format_text_newline


def main(config: ParsePageConfig):
    driver = start_driver()
    driver.get(config.url)

    # save full HTML
    save_to_path(
        content=driver.page_source,
        page_id=config.site_id,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        filename=PAGE_CONTENT_FILENAME,
    )

    # parse page for LLM context
    root_elem = BeautifulSoup(driver.page_source).find()
    text_list, elems, elem_groups = recurse_get_context(driver=driver, s=root_elem)

    # insert element idx annotations and same-class group insert identifiers
    group_idx = 0
    element_idx = 0
    annotated_text = []
    for t, e in zip(text_list, elems):
        if t:
            #ref = ElementReference(idx=element_idx, xpath=e.xpath) TODO annotate with xpath as well
            annotated_text += [ANNOTATE_IDX_IDENTIFIER.format(element_idx), t]
            element_idx += 1
        else:
            if element_idx:
                annotated_text += [CLOSE_ANNOTATE_IDX_IDENTIFIER.format(element_idx - 1)]
            annotated_text += [INSERT_IDX_IDENTIFIER.format(group_idx)]
            group_idx += 1
    annotated_text = "\n".join(annotated_text)

    # save parsed context
    parse_config_id = f"{config.min_class_overlap}co_{config.min_num_matches}nm"
    save_to_path(
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
            annotated_text += [ANNOTATE_IDX_IDENTIFIER.format(j), format_text_newline(e.soup.get_text())]
        annotated_text = "\n".join(annotated_text)

        save_to_path(
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

    import os
    from cache.util import load_from_path, get_load_path, get_workdir, PAGE_CONTENT_FILENAME
    from browser.chromedriver import start_driver

    workdir = get_workdir()
    test_content = load_from_path(
        page_id="fandango.com",
        session_id="fandango",
        cache_dir="example",
        filename=PAGE_CONTENT_FILENAME,
    )
    test_content_path = get_load_path(
        page_id="fandango.com",
        session_id="fandango",
        cache_dir="example",
        filename=PAGE_CONTENT_FILENAME,
    )
    root_elem = BeautifulSoup(test_content).find()
    driver = start_driver()
    driver.get(f"file://{os.path.join(workdir, test_content_path)}")
    text_list, elems, elem_groups = recurse_get_context(driver=driver, s=root_elem)
    print("\n".join(text_list))

    # check text context of same group elements
    for i, g in enumerate(elem_groups):
        print(f"Group {i} -----")
        for e in g.elems[:2]:
            print(e.soup.get_text())
            print("-----")

    # verify functionality of group context insertion
    assert len(text_list) == len(elems)