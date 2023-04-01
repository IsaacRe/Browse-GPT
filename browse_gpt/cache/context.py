import os

from .util import DEFAULT_CACHE_DIR, get_subdir_path, get_save_path


CONTEXT_SUBDIR = "parsed-context"


def get_parsed_context_path(filename: str, page_id: str, session_id: str, cache_dir: str) -> str:
    rel_path = get_save_path(filename=filename, session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=CONTEXT_SUBDIR)
    return os.path.abspath(rel_path)


def save_parsed_context(parsed_context: str, save_filename: str, page_id: str, session_id: str, cache_dir: str = DEFAULT_CACHE_DIR):
    with open(get_save_path(filename=save_filename, session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=CONTEXT_SUBDIR), "w+") as f:
        f.write(parsed_context)


def load_parsed_context(filename: str, page_id: str, session_id: str, cache_dir: str = DEFAULT_CACHE_DIR) -> str:
    with open(os.path.join(get_subdir_path(session_id=session_id, cache_dir=cache_dir, page_id=page_id, subdir=CONTEXT_SUBDIR), filename), "r") as f:
        return f.read()
