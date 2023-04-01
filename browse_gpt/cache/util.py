from os import makedirs
import os
import re
from dataclasses import dataclass
from typing import List, Tuple

from ..config import ParsePageConfig

DEFAULT_CACHE_DIR = ".cache"
PARSED_CONTEXT_FILENAME = "parsed-context.txt"
DESCRIPTION_INSERTED_CONTEXT_FILENAME = "description-inserted-content.txt"
PAGE_GROUP_DESCRIPTIONS_FILENAME = "extracted-group-descriptions.txt"
PAGE_CONTENT_FILENAME = "full.html"
EXTRACTED_CONTENT_GROUP_SUBDIR = "extracted-group-context"
ANNOTATE_IDX_IDENTIFIER = "%<{}%>"
CLOSE_ANNOTATE_IDX_IDENTIFIER = "%</{}%>"
INSERT_IDX_IDENTIFIER = "%[{}%]"

ANNOTATE_IDX_RE = re.compile(r"%<[^%]+%>")
INSERT_IDX_RE = re.compile(r"%\[[^%]+%\]")


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


def save_to_cache(content: str, filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None):
    with open(get_save_path(filename=filename, session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir), "w+") as f:
        f.write(content)


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

    def insert(self, *insertions: str) -> str:
        text = self.annotated_text
        for insertion in insertions:
            text = INSERT_IDX_RE.sub(insertion, text, count=1)
        return text


# TODO generalize below classes to allow nested context extraction
class ElementGroupContext(Context):
    def __init__(self, annotated_text: str, context_file: str):
        super().__init__(annotated_text)
        self.context_file = context_file


class PageContext(Context):
    def __init__(self, annotated_text: str, context_dir: str):
        super().__init__(annotated_text)
        self.context_dir = context_dir

    @staticmethod
    def from_config(cfg: ParsePageConfig) -> str:
        text, path = load_from_cache(
            filename=PARSED_CONTEXT_FILENAME,
            session_id=cfg.session_id,
            cache_dir=cfg.cache_dir,
            page_id=cfg.site_id,
            subdir=get_parse_config_id(min_class_overlap=cfg.min_class_overlap, min_num_matches=cfg.min_num_matches),
        )
        return PageContext(annotated_text=text, context_dir=os.path.dirname(path))
    
    def get_extracted_group_context(self) -> List[ElementGroupContext]:
        extracted_groups_dir = os.path.join(self.context_dir, EXTRACTED_CONTENT_GROUP_SUBDIR)
        group_ctx = []
        for f in listdir(extracted_groups_dir):
            path = os.path.join(extracted_groups_dir, f)
            content = load_from_path(path)
            group_ctx += [ElementGroupContext(annotated_text=content, context_file=path)]
        return group_ctx
