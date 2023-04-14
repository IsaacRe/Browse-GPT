from typing import List, Tuple
from sqlalchemy import text

from ..processing import DecoratedSoup, DecoratedSoupGroup
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
                    context=context,
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
                        context=e_.context,
                    )
                    db_session.add(element)
                
                element_ids += [parent_element.id]
            else:
                element = Element(
                    page_id=page_id,
                    element_position=i,
                    xpath=e.xpath,
                    outer_html=str(e.soup),
                    context=e.context,
                )
                db_session.add(element)
                db_session.commit()

                element_ids += [element.id]

        return element_ids


# task_id | element_id
def add_filtered_elements(db_client: DBClient, task_id: int, filtered_element_ids: List[int]) -> List[int]:
    with db_client.transaction() as db_session:
        for element_id in filtered_element_ids:
            filtered_elem = FilteredElement(
                task_id=task_id,
                element_id=element_id,
            )
            db_session.add(filtered_elem)


def get_filtered_elements(db_client: DBClient, task_id: int, page_id: int) -> List[Tuple[int, str]]:
    with db_client.transaction() as db_session:
        return db_session.execute(
            text("""
                SELECT elements.id, xpath
                FROM elements
                JOIN filtered_elements ON element_id = elements.id
                WHERE
                    task_id = :task_id
                    AND page_id = :page_id
            """),
            {"task_id": task_id, "page_id": page_id},
        ).fetchall()
