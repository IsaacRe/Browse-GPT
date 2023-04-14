from dataclasses import asdict
from typing import Tuple
from sqlalchemy import text

from ..db import DBClient
from ..model import Session
from ..config import CommonConfig


# tag | config
def new_session(db_client: DBClient, config: CommonConfig) -> Tuple[int, bool]:
    with db_client.transaction() as db_session:
        session = db_session.query(Session).filter(Session.tag == config.session_id).one_or_none()
        if session is not None:
            return session.id, True
        session = Session(tag=config.session_id, config=asdict(config))
        db_session.add(session)
        db_session.commit()
        return session.id, False


def clear_session_cache(db_client: DBClient, session_tag: str):
    with db_client.transaction() as db_session:
        q = db_session.query(Session).filter(Session.tag == session_tag)
        count = q.count()
        q.delete()
        return count
