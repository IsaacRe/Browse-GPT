import sys
from argparse import ArgumentParser, _ArgumentGroup
from dataclasses import dataclass, fields, asdict
from typing import ClassVar, Any, List

from .processing import MIN_CLASS_OVERLAP, MIN_NUM_MATCHES


_PARSER = ArgumentParser()


def make_arg(*name_or_flags, type: type = None, default: Any = None, dest: str = None, choices: List[Any] = None) -> "Argument":
    return Argument(
        name_or_flags=list(name_or_flags),
        type=type,
        default=default,
        dest=dest,
        choices=choices,
    )


@dataclass
class Argument:
    name_or_flags: List[str]
    type: type
    default: Any
    dest: str
    choices: List[Any]


class ConfigBase:
    _args: ClassVar[_ArgumentGroup] = None

    @classmethod
    def _add_args(cls):
        for f in fields(cls):
            arg: Argument = f.type
            arg_params = {k: v for k, v in asdict(arg).items() if k != "name_or_flags"}
            cls._args.add_argument(*arg.name_or_flags, **arg_params)

    @classmethod
    def parse_args(cls) -> "ConfigBase":
        #cls._add_args()
        # initialize config with default values
        cfg = cls(**{f.name: f.type.default for f in fields(cls)})

        # add parsed arguments
        cls._add_args()
        parsed_args = _PARSER.parse_args().__dict__
        for a, v in parsed_args.items():
            setattr(cfg, a, v)

        cfg.post_init(**parsed_args)
        return cfg
    
    def post_init(cls, **_: Any):
        pass


@dataclass
class CommonConfig(ConfigBase):
    url: make_arg("--url", type=str)
    session_id: make_arg("--session-id", type=str, default="1")
    cache_dir: make_arg("--cache-dir", type=str, default=".cache")


@dataclass
class CrawlPageConfig(CommonConfig):
    _args: ClassVar[_ArgumentGroup] = _PARSER.add_argument_group()

    site_id: make_arg("--site-id", type=str, default="")

    def post_init(self, url: str, **_):
        if not self.site_id:
            self.site_id = url.split('//')[1].replace('/', '|')


@dataclass
class ParsePageConfig(CrawlPageConfig):
    _args: ClassVar[_ArgumentGroup] = _PARSER.add_argument_group()

    min_class_overlap: make_arg("--min-class-overlap", type=int, default=MIN_CLASS_OVERLAP)
    min_num_matches: make_arg("--min-num-matches", type=int, default=MIN_NUM_MATCHES)


@dataclass
class BrowingSessionConfig(CommonConfig):
    _args: ClassVar[_ArgumentGroup] = _PARSER.add_argument_group()


def _test():
    sys.argv += ["--url", "https://grubhub.com"]
    cfg = CrawlPageConfig.parse_args()
    print(cfg)


if __name__ == "__main__":
    _test()