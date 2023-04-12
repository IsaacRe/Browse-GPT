from typing import List
from sqlalchemy import text
from ..db import DBClient


def get_context_for_page(db_client: DBClient, url_hash: str) -> str:
    with db_client.transaction() as db_session:
        return db_session.execute(
            text("""
                SELECT
                    elements.id,
                    COALESCE(description, context) AS context,
                    xpath
                FROM elements
                JOIN pages ON pages.id = page_id
                WHERE pages.url_hash = :url_hash
                    AND context != ''
                    AND is_root
            """),
            {"url_hash": url_hash},
        ).fetchall()


def get_group_context_for_page(db_client: DBClient, url_hash: str):
    with db_client.transaction() as db_session:
        return db_session.execute(
            text("""
                SELECT t2.element_position, string_agg(t1.context, '\\n') context
                FROM elements t1
                JOIN elements t2 ON t1.parent_id = t2.id
                JOIN pages ON pages.id = t2.page_id
                WHERE pages.url_hash = :url_hash
                    AND t1.context != ''
                    AND NOT t1.is_root
                GROUP BY t2.id, t2.element_position
            """),
            {"url_hash": url_hash},
        ).fetchall()


def update_group_description_for_page(db_client: DBClient, url_hash: str, positions: List[int], descriptions: List[str]):
    with db_client.transaction() as db_session:
        db_session.execute(
            text("""
                WITH inputs AS (
                    SELECT
                        unnest(:positions ::bigint[]) AS position,
                        unnest(:descriptions ::text[]) AS description,
                        id AS page_id
                    FROM pages
                    WHERE url_hash = :url_hash
                )
                UPDATE elements
                SET description = inputs.description
                FROM inputs
                WHERE
                    elements.page_id = inputs.page_id
                    AND elements.element_position = inputs.position
            """),
            {"url_hash": url_hash, "positions": list(positions), "descriptions": list(descriptions)},
        )
