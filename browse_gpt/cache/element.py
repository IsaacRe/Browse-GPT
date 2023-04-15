from typing import List, Tuple
from sqlalchemy import text

from ..processing import DecoratedSoup, DecoratedSoupGroup, format_text_newline
from ..model import Element, FilteredElement
from ..db import DBClient


# page_id | is_root | is_leaf | parent_id | xpath | element_position | outer_html | context | description
def add_elements(db_client: DBClient, page_id: int, elements: List[DecoratedSoup]) -> List[int]:
    element_ids = []
    with db_client.transaction() as db_session:
        for i, e in enumerate(elements):
            if isinstance(e, DecoratedSoupGroup):
                context = "\n".join([e_.context for e_ in e.elems])
                parent_element = Element(
                    page_id=page_id,
                    xpath=e.group_xpath,
                    element_position=i,
                    outer_html=str(e.soup.parent),  # TODO Change: currently DecoratedSoupGroup sets soup to first element
                    is_leaf=False,
                    context=format_text_newline(context),
                )
                db_session.add(parent_element)
                db_session.commit()

                for j, e_ in enumerate(e.elems):
                    element = Element(
                        page_id=page_id,
                        parent_id=parent_element.id,
                        xpath=e_.xpath,
                        element_position=j,
                        outer_html=str(e_.soup),
                        is_root=False,
                        context=format_text_newline(e_.context),
                    )
                    db_session.add(element)
                
                element_ids += [parent_element.id]
            else:
                element = Element(
                    page_id=page_id,
                    element_position=i,
                    xpath=e.xpath,
                    outer_html=str(e.soup),
                    context=format_text_newline(e.context),
                )
                db_session.add(element)
                db_session.commit()

                element_ids += [element.id]

        return element_ids


# task_id | element_id
def add_filtered_elements(
        db_client: DBClient,
        task_id: int,
        filtered_element_ids: List[int],
        filtered_descriptions: List[str] = None,
) -> List[int]:
    if filtered_descriptions is None:
        filtered_descriptions = [None] * len(filtered_element_ids)
    with db_client.transaction() as db_session:
        for element_id, description in zip(filtered_element_ids, filtered_descriptions):
            filtered_elem = FilteredElement(
                task_id=task_id,
                element_id=element_id,
                description=description,
            )
            db_session.add(filtered_elem)


def get_filtered_elements(db_client: DBClient, task_id: int, page_id: int) -> List[Tuple[int, str]]:
    with db_client.transaction() as db_session:
        return db_session.execute(
            text("""
                SELECT elements.id, outer_html, xpath
                FROM elements
                JOIN filtered_elements ON element_id = elements.id
                WHERE
                    task_id = :task_id
                    AND page_id = :page_id
            """),
            {"task_id": task_id, "page_id": page_id},
        ).fetchall()
