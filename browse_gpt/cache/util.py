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


def get_context_for_page_id(db_client: DBClient, page_id: str) -> str:
    with db_client.transaction() as db_session:
        return db_session.execute(
            text("""
                SELECT
                    id,
                    COALESCE(description, context) AS context,
                    xpath
                FROM elements
                WHERE page_id = :page_id
                    AND context != ''
                    AND is_root
            """),
            {"page_id": page_id},
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
    

def get_group_context_for_page_id(db_client: DBClient, page_id: str):
    with db_client.transaction() as db_session:
        return db_session.execute(
            text("""
                SELECT t2.id, t2.element_position, string_agg(t1.context, '\\n') context
                FROM elements t1
                JOIN elements t2 ON t1.parent_id = t2.id
                WHERE t2.page_id = :page_id
                    AND t1.context != ''
                    AND NOT t1.is_root
                GROUP BY t2.id, t2.element_position
            """),
            {"page_id": page_id},
        ).fetchall()


def get_filtered_context_for_page(db_client: DBClient, task_description: str, url_hash: str):
    with db_client.transaction() as db_session:
        return db_session.execute(
            text("""
                SELECT elements.id, xpath
                FROM filtered_elements
                JOIN elements ON element_id = elements.id
                JOIN tasks ON task_id = tasks.id
                JOIN pages ON page_id = pages.id
                WHERE
                    tasks.context = :task_description
                    AND pages.url_hash = :url_hash
            """),
            {"task_description": task_description, "url_hash": url_hash},
        ).fetchall()


def update_group_description_for_page(db_client: DBClient, url_hash: int, positions: List[int], descriptions: List[str]):
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


def update_group_description_for_page_id(db_client: DBClient, element_ids: List[int], descriptions: List[str]):
    with db_client.transaction() as db_session:
        db_session.execute(
            text("""
                WITH inputs AS (
                    SELECT
                        unnest(:element_ids ::bigint[]) AS element_id,
                        unnest(:descriptions ::text[]) AS description
                )
                UPDATE elements
                SET description = inputs.description
                FROM inputs
                WHERE elements.id = inputs.element_id
            """),
            {"element_ids": list(element_ids), "descriptions": list(descriptions)},
        )


def get_file_url(path: str) -> str:
    return f"file://{path}"


from os import makedirs
import os
import re
from dataclasses import dataclass
from typing import List, Tuple

from ..config import ParsePageConfig

MAX_ANNOTATION_ITER = 1000
DEFAULT_CACHE_DIR = ".cache"
PARSED_CONTEXT_FILENAME = "parsed-context.txt"
DESCRIPTION_INSERTED_CONTEXT_FILENAME = "description-inserted-content.txt"
PAGE_GROUP_DESCRIPTIONS_FILENAME = "extracted-group-descriptions.txt"
FILTERED_CONTEXT_FILENAME = "filtered-context.txt"
FILTERED_HTML_FILENAME = "filtered.html"
PAGE_HTML_FILENAME = "full.html"
EXTRACTED_CONTENT_GROUP_SUBDIR = "extracted-group-context"
ANNOTATE_IDX_IDENTIFIER = "%<{}%>"
CLOSE_ANNOTATE_IDX_IDENTIFIER = "%</{}%>"
INSERT_IDX_IDENTIFIER = "%[{}%]"

ANNOTATE_IDX_RE = re.compile(r"%<([^%]+)%>")
INSERT_IDX_RE = re.compile(r"%\[[^%]+%\]")


# TODO debug
def parse_annotated_content(annotated_content_string: str) -> List[Tuple[str, str]]:
    content = []
    identifier = ""
    annotated_content = []
    for l in annotated_content_string.split("\n"):
        found = ANNOTATE_IDX_RE.search(l)
        if found:
            _, upto = found.span()
            remaining = l[upto:].strip()
            if ANNOTATE_IDX_RE.search(remaining):
                raise Exception(f"Found multiple annotations on single line: {l}")
            identifier_, = found.groups()
            if identifier_.startswith("/"):
                identifier_ = identifier_[1:]
                if identifier_ and identifier_ != identifier:
                    raise Exception(f"Mismatch in closing annotation: `{identifier_}` != `{identifier}`")
                annotated_content += [(identifier, "\n".join(content))]
                identifier = ""
                content = [remaining] if remaining else []
                continue
            if identifier:
                annotated_content += [(identifier, "\n".join(content))]
            content = [remaining] if remaining else []
            identifier = identifier_
            continue
        content += [l]
    # append content for final annotation
    if identifier:
        annotated_content += [(identifier, "\n".join(content))]
    return annotated_content


def get_workdir() -> str:
    return os.getcwd()


def get_subdir_path(session_id: str, cache_dir: str, page_id: str, subdir: str = None) -> str:
    path = os.path.join(cache_dir, session_id, page_id)
    if subdir:
        path = os.path.join(path, subdir)
    return path


def get_save_path(filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None) -> str:
    dir = get_subdir_path(session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir)
    makedirs(dir, exist_ok=True)
    return os.path.join(dir, filename)


def save_to_path(content: str, path: str) -> str:
    with open(path, "w+") as f:
        f.write(content)
    return path


def save_to_cache(content: str, filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None) -> str:
    path = get_save_path(filename=filename, session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir)
    return save_to_path(content=content, path=path)


def get_load_path(filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None) -> str:
    dir = get_subdir_path(session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir)
    return os.path.join(dir, filename)


def load_from_path(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def load_from_cache(filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None) -> Tuple[str, str]:
    path = get_load_path(filename=filename, session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir)
    return load_from_path(path), path


def get_parse_config_id(min_class_overlap: int, min_num_matches: int) -> str:
    return f"{min_class_overlap}co_{min_num_matches}nm"


def listdir(path: str):
    makedirs(path, exist_ok=True)
    return os.listdir(path)


def remove_xpath_from_ann(ann: str):
    try:
        idx = ann.split(":")[0]
    except IndexError:
        raise Exception(f"Failed to prepare annotation `{ann}`")
    return ANNOTATE_IDX_IDENTIFIER.format(idx)


def get_idx_xpath_from_ann(ann: str):
    try:
        idx, xpath = ann.split(":")
    except ValueError:
        raise Exception(f"Failed to get idx and xpath from annotation `{ann}`")
    return idx, xpath


@dataclass
class ElementReference:
    idx: int
    xpath: str

    def to_str(self) -> str:
        return f"{self.idx}:{self.xpath}"


class Context:
    def __init__(self, annotated_text):
        self.annotated_text = annotated_text
        self.raw_text = ANNOTATE_IDX_RE.sub("", INSERT_IDX_RE.sub("", annotated_text))

    """Takes tuples of (insertion index, insertion string) pairs and inserts string
    in order by index"""
    def insert(self, *insertions: Tuple[str, str]) -> str:
        text = self.annotated_text
        # order by insertion index
        for _, insertion in sorted(insertions, key=lambda x: int(x[0])):
            text = INSERT_IDX_RE.sub(insertion, text, count=1)
        return text
    
    def parse_annotation(self) -> List[Tuple[str, str]]:
        return parse_annotated_content(self.annotated_text)
    
    """Applies the given function to indentifier of each annotation and removes
    trailing newlines so that annotation and text appear on the same line"""
    def prepare_annotated_text(self, ann_fn) -> str:
        prepared_text = []
        for ann, text in self.parse_annotation():
            new_ann = ann_fn(ann)
            prepared_text += [ANNOTATE_IDX_IDENTIFIER.format(new_ann) + " " + text]
        return "\n".join(prepared_text)


# TODO generalize below classes to allow nested context extraction
class ElementGroupContext(Context):
    def __init__(self, annotated_text: str, context_file: str):
        super().__init__(annotated_text)
        self.context_file = context_file


class PageContext(Context):
    def __init__(self, annotated_text: str, context_dir: str, parse_config_id: str = ""):
        super().__init__(annotated_text)
        self.context_dir = context_dir
        self.parse_config_id = parse_config_id


class FullPageContext(PageContext):
    _filename = PAGE_HTML_FILENAME

    @classmethod
    def from_config(cls, cfg: ParsePageConfig) -> "PageContext":
        text, path = load_from_cache(
            filename=cls._filename,
            session_id=cfg.session_id,
            cache_dir=cfg.cache_dir,
            page_id=cfg.site_id,
        )
        return cls(
            annotated_text=text,
            context_dir=os.path.dirname(path),
            parse_config_id=get_parse_config_id(
                min_class_overlap=cfg.min_class_overlap,
                min_num_matches=cfg.min_num_matches,
            ),
        )
    

class ParsedPageContext(PageContext):
    _filename = PARSED_CONTEXT_FILENAME

    @classmethod
    def from_config(cls, cfg: ParsePageConfig) -> "PageContext":
        parse_config_id = get_parse_config_id(
            min_class_overlap=cfg.min_class_overlap,
            min_num_matches=cfg.min_num_matches,
        )
        text, path = load_from_cache(
            filename=cls._filename,
            session_id=cfg.session_id,
            cache_dir=cfg.cache_dir,
            page_id=cfg.site_id,
            subdir=parse_config_id,
        )
        return cls(
            annotated_text=text,
            context_dir=os.path.dirname(path),
            parse_config_id=parse_config_id,
        )

    def get_extracted_group_context(self) -> List[ElementGroupContext]:
        extracted_groups_dir = os.path.join(self.context_dir, EXTRACTED_CONTENT_GROUP_SUBDIR)
        group_ctx = []
        for f in listdir(extracted_groups_dir):
            group_idx = f.split(".")[0]
            path = os.path.join(extracted_groups_dir, f)
            content = load_from_path(path)
            group_ctx += [(group_idx, ElementGroupContext(annotated_text=content, context_file=path))]
        return group_ctx


class EmbellishedPageContext(ParsedPageContext):
    _filename = DESCRIPTION_INSERTED_CONTEXT_FILENAME

    def __init__(self, annotated_text: str, context_dir: str, parse_config_id: str = ""):
        super().__init__(annotated_text, context_dir, parse_config_id=parse_config_id)
        self.content_idx = {}

    def populate_content_idx(self):
        for id_, ctx in self.parse_annotation():
            idx = remove_xpath_from_ann(id_)
            self.content_idx[idx] = ctx


class FilteredPageContext(PageContext):
    _filename = FILTERED_CONTEXT_FILENAME
