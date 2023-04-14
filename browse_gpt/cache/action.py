from dataclasses import dataclass
from enum import Enum
from typing import Dict
from undetected_chromedriver import WebElement, Chrome
from selenium.webdriver.common.keys import Keys
from sqlalchemy import text

from ..db import DBClient
from ..model import Action

ACTION_TYPE_KEY = "action_type"
INPUT_TEXT_KEY = "input_text"


# task_id | element_id | new_page_id | action_position | metadata | description
def new_action(
    db_client: DBClient,
    task_id: int,
    element_id: int,
    action_spec: "ActionSpec",
) -> int:
    with db_client.transaction() as db_session:
        action = Action(
            task_id=task_id,
            element_id=element_id,
            action_position=0,
            metadata_=action_spec.to_json(),
        )
        db_session.add(action)
        db_session.commit()
        return action.id
    

def update_action_result(db_client: DBClient, action_id: int, new_page_id: int):
    with db_client.transaction() as db_session:
        db_session.execute(
            text("""
                UPDATE actions
                SET new_page_id = :new_page_id
                WHERE id = :action_id
            """),
            {"action_id": action_id},
        )


class ElementActionType(Enum):
    CLICK = 1
    INPUT_KEYS = 2
    INPUT_KEYS_ENTER = 3

    def needs_input(self):
        return self.value in [2, 3]


@dataclass
class ActionSpec:
    action_type: ElementActionType
    input_text: str = None

    def __post_init__(self):
        if self.action_type.needs_input() and self.input_text is None:
            raise Exception("Action requires input but no input was given")

    def to_json(self) -> Dict[str, str]:
        return {
            ACTION_TYPE_KEY: self.action_type.value,
            INPUT_TEXT_KEY: self.input_text,
        }
    
    @staticmethod
    def from_json(obj: Dict[str, str]) -> "ActionSpec":
        return ActionSpec(
            action_type=ElementActionType[obj[ACTION_TYPE_KEY]],
            input_text=obj[INPUT_TEXT_KEY],
        )

    def run(self, driver: Chrome, e: WebElement):
        if self.action_type == ElementActionType.CLICK:
            e.click()
        elif self.action_type in [
            ElementActionType.INPUT_KEYS, 
            ElementActionType.INPUT_KEYS_ENTER,
        ]:
            e.send_keys(self.input_text)
            driver.implicitly_wait(1)
            if self.action_type == ElementActionType.INPUT_KEYS_ENTER:
                e.send_keys(Keys.ENTER)
