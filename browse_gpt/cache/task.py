from ..db import DBClient
from ..model import Task


# session_id | is_root | is_leaf | parent_id | subtask_position | context
def new_task(
    db_client: DBClient,
    session_id: int,
    task_description: str,
    parent_id: int = None,
) -> int:
    with db_client.transaction() as db_session:
        subtask_position = 0 
        task = db_session.query(Task) \
                .filter(Task.session_id == session_id) \
                .filter(Task.parent_id == parent_id) \
                .filter(Task.subtask_position == subtask_position) \
                .one_or_none()
        if task is not None:
            return task.id, True
        task = Task(
            session_id=session_id,
            is_root=parent_id is None,
            is_leaf=True,
            parent_id=parent_id,
            subtask_position=subtask_position,
            context=task_description,
        )
        db_session.add(task)
        db_session.commit()
        return task.id, False
