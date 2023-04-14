from dataclasses import dataclass
from enum import Enum
from typing import List
import os
import openai
import logging

from ..util import timer

OPENAI_DEFAULT_CHAT_MODEL = "gpt-3.5-turbo"

logger = logging.getLogger(__name__)


def set_api_key(key: str):
    openai.api_key = key


def extract_response(chat_api_response):
    return OpenAIChatMessage(**chat_api_response["choices"][0]["message"])


def complete_chat(context: List["OpenAIChatMessage"], openai_model: str = OPENAI_DEFAULT_CHAT_MODEL) -> "OpenAIChatMessage":
    result = openai.ChatCompletion.create(
        model=openai_model,
        messages=[ctx.asdict() for ctx in context],
    )
    return extract_response(result)


def single_response(message: str, openai_model: str = OPENAI_DEFAULT_CHAT_MODEL) -> "OpenAIChatMessage":
    logger.info(f"Querying OpenAI API (message length={len(message)})...")
    logger.debug(f'Message: """{message}"""')
    with timer() as t:
        response = complete_chat(context=[OpenAIChatMessage(content=message)], openai_model=openai_model).content
    logger.info(f"Done. ({t.seconds()}s)")
    logger.debug(f'Response: """{response}"""')
    return response


class OpenAIChatMessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class OpenAIChatMessage:
    content: str
    role: OpenAIChatMessageRole = OpenAIChatMessageRole.USER

    def asdict(self):
        return {"role": self.role.value, "content": self.content}


def _test():
    set_api_key(os.getenv("OPENAI_API_KEY"))
    print(single_response("Hello world").content)


if __name__ == "__main__":
    _test()
