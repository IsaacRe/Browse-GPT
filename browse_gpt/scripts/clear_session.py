import sys
import logging

from browse_gpt.config import CommonConfig
from browse_gpt.db import DBClient
from browse_gpt.cache.session import clear_session_cache

logger = logging.getLogger(__name__)


def main(config: CommonConfig):
    db_client = DBClient(config.db_url)

    logger.info(f"Deleting cache for session '{config.session_id}'")
    del_count = clear_session_cache(db_client=db_client, session_tag=config.session_id)
    logger.info(f"Deleted {del_count} items.")

    return 0


if __name__ == "__main__":
    sys.exit(main(CommonConfig.parse_args()))
