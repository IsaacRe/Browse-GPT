import sys
from argparse import ArgumentParser, _ArgumentGroup
from dataclasses import dataclass, fields, asdict
from enum import Enum
from typing import ClassVar, Any, List
import os
import os.path

from .util import hash_url
from .logging import setup_logger, LOG_LEVELS
from .db import DBClient

MIN_CLASS_OVERLAP = 6  # test cases so far min=5, max=28
MIN_NUM_MATCHES = 3
ENV_VAR_FLAG_PREFIX = "ACT_APP"

_PARSER = ArgumentParser()


def make_arg(*name_or_flags, type: type = None, default: Any = None, dest: str = None, choices: List[Any] = None) -> "Argument":
    return Argument(
        name_or_flags=list(name_or_flags),
        type=type,
        default=default,
        dest=dest,
        choices=choices,
    )


def get_env_for_flag(flag: str) -> str:
    varname = "_".join([ENV_VAR_FLAG_PREFIX, flag.upper().strip("-").replace("-", "_")])
    return os.getenv(varname)


@dataclass
class Argument:
    name_or_flags: List[str]
    type: type
    default: Any
    dest: str
    choices: List[Any]


class OverrideOptions(Enum):
    ALWAYS = 1
    ON_FAILURE = 2
    NEVER = 3


class ConfigBase:
    _args: ClassVar[_ArgumentGroup] = None
    _ignore: ClassVar[List[str]] = []

    @classmethod
    def _add_args(cls):
        for f in fields(cls):
            if f.name not in cls._ignore:
                arg: Argument = f.type
                arg_params = {k: v for k, v in asdict(arg).items() if k != "name_or_flags"}
                
                # check if flag has been set with environment variable
                env_value = get_env_for_flag(arg.name_or_flags[0])
                if env_value is not None:
                    ArgType = arg_params.get("type")
                    if ArgType is not None:
                        env_value = ArgType(env_value)
                    arg_params["default"] = env_value

                cls._args.add_argument(*arg.name_or_flags, **arg_params)

    @classmethod
    def parse_args(cls, allow_unknown: bool = False) -> "ConfigBase":
        # initialize config with default values
        cfg = cls(
            **{f.name: None if f.name in cls._ignore else f.type.default for f in fields(cls)}
        )

        # add parsed arguments
        cls._add_args()
        if allow_unknown:
            parsed_args, _ = _PARSER.parse_known_args()
            parsed_args = parsed_args.__dict__
        else:
            parsed_args = _PARSER.parse_args().__dict__
        for a, v in parsed_args.items():
            setattr(cfg, a, v)

        cfg.post_init(**parsed_args)
        return cfg
    
    def post_init(self, **_: Any):
        pass


@dataclass
class CommonConfig(ConfigBase):
    _args: ClassVar[_ArgumentGroup] = _PARSER.add_argument_group()
    _ignore: ClassVar[List[str]] = ["db_client"]

    log_level: make_arg("--log-level", type=str, choices=list(LOG_LEVELS), default="info")
    url: make_arg("--url", type=str)
    session_id: make_arg("--session-id", type=str, default="1")
    cache_dir: make_arg("--cache-dir", type=str, default=".cache")
    db_url: make_arg("--db-url", type=str, default="postgresql://root:root@0.0.0.0/browse-gpt-db")
    db_client: DBClient

    def post_init(self, log_level: str, cache_dir: str, **_: Any):
        setup_logger(log_level)
        self.cache_dir = os.path.join(os.getcwd(), cache_dir)
        self.db_client = DBClient(self.db_url)

    def asdict(self):
        ret_dict = {}
        for f in fields(self):
            if f.name not in self._ignore:
                value = getattr(self, f.name)
                if isinstance(value, Enum):
                    value = value.value
                ret_dict[f.name] = value
        return ret_dict


@dataclass
class CrawlPageConfig(CommonConfig):
    _args: ClassVar[_ArgumentGroup] = _PARSER.add_argument_group()

    site_id: make_arg("--site-id", type=str, default="")

    def post_init(self, url: str, **kwargs):
        super().post_init(**kwargs)
        if not self.site_id:
            self.site_id = hash_url(url)


@dataclass
class ParsePageConfig(CrawlPageConfig):
    _args: ClassVar[_ArgumentGroup] = _PARSER.add_argument_group()

    min_class_overlap: make_arg("--min-class-overlap", type=int, default=MIN_CLASS_OVERLAP)
    min_num_matches: make_arg("--min-num-matches", type=int, default=MIN_NUM_MATCHES)


@dataclass
class TaskExecutionConfig(ParsePageConfig):
    _args: ClassVar[_ArgumentGroup] = _PARSER.add_argument_group()

    llm_site_id: make_arg("--llm-site-id", type=str, default="")
    task_description: make_arg("--task-description", type=str)

    def post_init(self, llm_site_id: str, **kwargs):
        super().post_init(**kwargs)
        # set identifier used in LLM interface to site_id if not explicitly set
        if not llm_site_id:
            self.llm_site_id = self.site_id
        if self.llm_site_id.isnumeric():
            raise Exception("LLM site ID should be a colloquial identifier of the site (not a numeric ID)")


@dataclass
class BrowingSessionConfig(TaskExecutionConfig):
    _args: ClassVar[_ArgumentGroup] = _PARSER.add_argument_group()

    browser_extension: make_arg("--browser-extension", type=str, default="")
    allow_override: make_arg("--allow-override", type=str, choices=["ALWAYS", "ON_FAILURE", "NEVER"], default="ALWAYS")

    def post_init(self, allow_override: str, **kwargs):
        super().post_init(**kwargs)
        self.allow_override = OverrideOptions[allow_override]


def _test():
    sys.argv += ["--url", "https://grubhub.com"]
    cfg = CrawlPageConfig.parse_args()
    print(cfg)


if __name__ == "__main__":
    _test()
