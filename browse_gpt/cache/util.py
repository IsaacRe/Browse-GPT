from os import makedirs
import os
import re
from dataclasses import dataclass

DEFAULT_CACHE_DIR = ".cache"
PARSED_CONTEXT_FILENAME = "parsed-context.txt"
PAGE_CONTENT_FILENAME = "full.html"
EXTRACTED_CONTENT_GROUP_SUBDIR = "extracted-group-context"
ANNOTATE_IDX_IDENTIFIER = "%<{}%>"
CLOSE_ANNOTATE_IDX_IDENTIFIER = "%</{}%>"
INSERT_IDX_IDENTIFIER = "%[{}%]"

ANNOTATE_IDX_RE = re.compile(r"%<[^%]+%>")
INSERT_IDX_RE = re.compile(r"%\[[^%]+%\]")


def get_workdir():
    return os.getcwd()


def get_subdir_path(session_id: str, cache_dir: str, page_id: str, subdir: str = None):
    path = os.path.join(cache_dir, session_id, page_id)
    if subdir:
        path = os.path.join(path, subdir)
    return path


def get_save_path(filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None) -> str:
    dir = get_subdir_path(session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir)
    makedirs(dir, exist_ok=True)
    return os.path.join(dir, filename)


def save_to_path(content: str, filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None):
    with open(get_save_path(filename=filename, session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir), "w+") as f:
        f.write(content)


def get_load_path(filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None) -> str:
    dir = get_subdir_path(session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir)
    return os.path.join(dir, filename)


def load_from_path(filename: str, session_id: str, cache_dir: str,  page_id: str, subdir: str = None) -> str:
    with open(get_load_path(filename=filename, session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=subdir), "r") as f:
        return f.read()


@dataclass
class ElementReference:
    idx: int
    xpath: str

    def to_str(self):
        return f"{self.idx}:{self.xpath}"
