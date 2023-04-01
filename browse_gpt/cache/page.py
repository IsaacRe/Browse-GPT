import os

from .util import DEFAULT_CACHE_DIR, get_subdir_path, get_save_path

PAGE_CONTENT_FILENAME = "full.html"


def get_page_content_path(page_id: str, session_id: str, cache_dir: str = DEFAULT_CACHE_DIR) -> str:
    rel_path = get_save_path(filename=PAGE_CONTENT_FILENAME, session_id=session_id, cache_dir=cache_dir, page_id=page_id)
    return os.path.abspath(rel_path)


def save_page(page_content: str, page_id: str, session_id: str, cache_dir: str = DEFAULT_CACHE_DIR):
    with open(get_save_path(filename=PAGE_CONTENT_FILENAME, session_id=session_id, cache_dir=cache_dir, page_id=page_id), "w+") as f:
        f.write(page_content)


def load_page_content(page_id: str, session_id: str, cache_dir: str = DEFAULT_CACHE_DIR) -> str:
    with open(get_save_path(filename=PAGE_CONTENT_FILENAME, session_id=session_id, cache_dir=cache_dir, page_id=page_id), "r") as f:
        return f.read()
