from dataclasses import asdict
from typing import Tuple

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
