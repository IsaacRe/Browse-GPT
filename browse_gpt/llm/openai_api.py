from dataclasses import dataclass
from enum import Enum
from typing import List
import os
import openai

OPENAI_DEFAULT_CHAT_MODEL = "gpt-3.5-turbo"


def set_api_key(key: str):
    openai.api_key = key


def extract_response(chat_api_response):
    return OpenAIChatMessage(**chat_api_response["choices"][0]["message"])


def complete_chat(context: List["OpenAIChatMessage"], openai_model: str = OPENAI_DEFAULT_CHAT_MODEL):
    result = openai.ChatCompletion.create(
        model=openai_model,
        messages=[ctx.asdict() for ctx in context],
    )
    return extract_response(result)


def single_response(message: str, openai_model: str = OPENAI_DEFAULT_CHAT_MODEL):
    return complete_chat(context=[OpenAIChatMessage(content=message)], openai_model=openai_model).content


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
