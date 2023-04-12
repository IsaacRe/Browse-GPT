import sqlalchemy
from sqlalchemy.orm.session import sessionmaker, Session


class DBClient:

    def __init__(self, db_url) -> None:
        self.db_url = db_url
        self.engine = sqlalchemy.create_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine)

    def transaction(self) -> "ContextManager":
        return ContextManager(self.session_factory)

    def session(self) -> Session:
        return self.session_factory()


class ContextManager:

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory
        self.session = None

    def __enter__(self) -> Session:
        self.session = self.session_factory()
        return self.session

    def __exit__(self, exc_type, exc_value, tb):
        if tb is None:
            self.session.commit()
        else:
            self.session.rollback()
