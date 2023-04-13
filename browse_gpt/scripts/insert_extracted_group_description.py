import sys
from browse_gpt.config import ParsePageConfig
from browse_gpt.db import DBClient
from browse_gpt.cache.util import get_group_context_for_page, update_group_description_for_page
from browse_gpt.prompt.interface import describe_selection


def main(config: ParsePageConfig):
    db_client = DBClient(config.db_url)

    group_context = get_group_context_for_page(db_client=db_client, url_hash=config.site_id)
    group_positions, group_descriptions = zip(*[
        (int(group_idx), describe_selection(group_ctx).split("\n")[0])
        for group_idx, group_ctx
        in group_context
    ])

    update_group_description_for_page(
        db_client=db_client,
        url_hash=config.site_id,
        positions=group_positions,
        descriptions=group_descriptions,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main(ParsePageConfig.parse_args()))
