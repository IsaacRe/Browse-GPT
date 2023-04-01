import sys
from browse_gpt.config import ParsePageConfig
from browse_gpt.cache.util import (
    save_to_cache,
    get_parse_config_id,
    PAGE_GROUP_DESCRIPTIONS_FILENAME,
    DESCRIPTION_INSERTED_CONTEXT_FILENAME,
    PageContext,
)
from browse_gpt.prompt.interface import describe_selection
from browse_gpt.cache.util import PageContext


def main(config: ParsePageConfig):
    page_ctx: PageContext = PageContext.from_config(config)
    group_descriptions = []
    for group_ctx in page_ctx.get_extracted_group_context():
        group_descriptions += [describe_selection(group_ctx).split("\n")[0]]
    group_descriptions_text = "\n".join(group_descriptions)

    parse_config_id = get_parse_config_id(min_class_overlap=config.min_class_overlap, min_num_matches=config.min_num_matches)

    save_to_cache(
        content=group_descriptions_text,
        filename=PAGE_GROUP_DESCRIPTIONS_FILENAME,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        page_id=config.site_id,
        subdir=parse_config_id,
    )

    # insert descriptions into original page context
    description_inserted_context = page_ctx.insert(*group_descriptions)

    # save description-inserted page context
    save_to_cache(
        content=description_inserted_context,
        filename=DESCRIPTION_INSERTED_CONTEXT_FILENAME,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        page_id=config.site_id,
        subdir=parse_config_id,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main(ParsePageConfig.parse_args()))
