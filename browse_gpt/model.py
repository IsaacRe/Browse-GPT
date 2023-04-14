from sqlalchemy import Column, BigInteger, Text, JSON, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"
    id = Column(BigInteger, primary_key=True)
    tag = Column(Text, nullable=False, unique=True)
    config = Column(JSON)
    pages = relationship("Page", backref="session")

class Page(Base):
    __tablename__ = "pages"
    id = Column(BigInteger, primary_key=True)
    session_id = Column(BigInteger, ForeignKey("sessions.id"), nullable=False)
    url = Column(Text, nullable=False)
    url_hash = Column(Text, index=True, nullable=False)
    content_path = Column(Text)
    elements = relationship("Element", backref="page")

    __table_args__ = (
        UniqueConstraint("session_id", "url_hash", name="pages_session_id_url_hash_uix"),
    )

class Element(Base):
    __tablename__ = "elements"
    id = Column(BigInteger, primary_key=True)
    page_id = Column(BigInteger, ForeignKey("pages.id"), nullable=False)
    is_root = Column(Boolean, index=True, server_default="t")
    is_leaf = Column(Boolean, index=True, server_default="t")
    parent_id = Column(BigInteger, ForeignKey("elements.id"))
    xpath = Column(Text, nullable=False)
    element_position = Column(BigInteger, nullable=False)
    outer_html = Column(Text, nullable=False)
    context = Column(Text, nullable=False)
    filtered_by = relationship("FilteredElement", backref="element")

    __table_args__ = (
        UniqueConstraint("page_id", "parent_id", "element_position", name="elements_page_id_parent_id_position_uix"),
    )

class Task(Base):
    __tablename__ = "tasks"
    id = Column(BigInteger, primary_key=True)
    session_id = Column(BigInteger, ForeignKey("sessions.id"), nullable=False)
    is_root = Column(Boolean, index=True, server_default="f")
    is_leaf = Column(Boolean, index=True, server_default="f")
    parent_id = Column(BigInteger, ForeignKey("tasks.id"), index=True)
    subtask_position = Column(BigInteger)
    context = Column(Text, nullable=False)
    actions = relationship("Action", backref="task")
    subtasks = relationship("Task", backref= "parent", remote_side=[id])

    __table_args__ = (
        UniqueConstraint("session_id", "parent_id", "subtask_position", name="tasks_session_id_parent_id_subtask_position_uix"),
    )

class Action(Base):
    __tablename__ = "actions"
    id = Column(BigInteger, primary_key=True)
    task_id = Column(BigInteger, ForeignKey("tasks.id"), nullable=False)
    element_id = Column(BigInteger, ForeignKey("elements.id"), index=True, nullable=False)
    new_page_id = Column(BigInteger, ForeignKey("pages.id"), index=True)
    action_position = Column(BigInteger, nullable=False)
    metadata_ = Column("metadata", JSON)  # 'metadata' is protected
    description = Column(Text)

    __table_args__ = (
        UniqueConstraint("task_id", "action_position", name="actions_task_id_action_position_uix"),
    )

class FilteredElement(Base):
    __tablename__ = "filtered_elements"
    id = Column(BigInteger, primary_key=True)
    task_id = Column(BigInteger, ForeignKey("tasks.id"), nullable=False)
    element_id = Column(BigInteger, ForeignKey("elements.id"), index=True, nullable=False)
    description = Column("description", Text)

    __table_args__ = (
        UniqueConstraint("task_id", "element_id", name="filtered_elements_task_id_element_id_uix"),
    )
