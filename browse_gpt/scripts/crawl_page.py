import sys
from bs4 import BeautifulSoup
from dataclasses import asdict

from browse_gpt.db import DBClient
import browse_gpt.model as orm
from browse_gpt.config import ParsePageConfig
from browse_gpt.browser.chromedriver import start_driver
from browse_gpt.cache.util import (
    save_to_cache,
    PAGE_HTML_FILENAME,
)
from browse_gpt.processing import recurse_get_context, get_decorated_elem, DecoratedSoupGroup


def main(config: ParsePageConfig):
    db_client = DBClient(config.db_url)

    driver = start_driver()
    driver.get(config.url)

    # save full HTML
    save_path = save_to_cache(
        content=driver.page_source,
        page_id=config.site_id,
        session_id=config.session_id,
        cache_dir=config.cache_dir,
        filename=PAGE_HTML_FILENAME,
    )

    # add session and page to db
    with db_client.transaction() as db_session:
        session = orm.Session(tag=config.session_id, config=asdict(config))
        db_session.add(session)
        db_session.commit()

        page = orm.Page(session_id=session.id, url=config.url, url_hash=config.site_id, content_path=save_path)
        db_session.add(page)
        db_session.commit()

        page_id = page.id

    # parse page for LLM context
    root_elem = BeautifulSoup(driver.page_source).find()
    ds = get_decorated_elem(driver=driver, soup=root_elem, parent_xpath="/", tag=root_elem.name, tag_index=0)
    _, elems, _ = recurse_get_context(driver=driver, ds=ds)

    # add elements to db
    with db_client.transaction() as db_session:
        for i, e in enumerate(elems):
            if isinstance(e, DecoratedSoupGroup):
                context = "\n".join([e_.context for e_ in e.elems])
                parent_element = orm.Element(
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
                    element = orm.Element(
                        page_id=page_id,
                        parent_id=parent_element.id,
                        xpath=e_.xpath,
                        element_position=j,
                        outer_html=str(e_.soup),
                        is_root=False,
                        context=e_.context,
                    )
                    db_session.add(element)
            else:
                element = orm.Element(
                    page_id=page_id,
                    element_position=i,
                    xpath=e.xpath,
                    outer_html=str(e.soup),
                    context=e.context,
                )
                db_session.add(element)

    return 0


if __name__ == "__main__":
    sys.exit(main(ParsePageConfig.parse_args()))
