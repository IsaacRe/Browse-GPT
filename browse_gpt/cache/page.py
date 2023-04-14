from ..db import DBClient
from ..model import Page
from ..util import hash_url
from ..config import CommonConfig
from .util import save_to_cache, PAGE_HTML_FILENAME


# session_id | url | url_hash | content_path
def new_page(db_client: DBClient, session_id: int, url: str, content: str, config: CommonConfig) -> int:
    url_hash = hash_url(url)
    with db_client.transaction() as db_session:
        session = db_session.query(Page) \
                    .filter(Page.session_id == session_id) \
                    .filter(Page.url_hash == url_hash) \
                    .one_or_none()
        if session is not None:
            return session.id, True
        
        # save page content
        content_path = save_to_cache(
            content=content,
            page_id=url_hash,
            session_id=config.session_id,
            cache_dir=config.cache_dir,
            filename=PAGE_HTML_FILENAME,
        )
        session = Page(session_id=session_id, url=url, url_hash=url_hash, content_path=content_path)
        db_session.add(session)
        db_session.commit()
        return session.id, False
