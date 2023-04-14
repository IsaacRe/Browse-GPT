"""
create tables for context, action and task caching

Revision ID: 8527a0419ed6
Down revision ID: None
Created date: 2023-04-06 15:04:39.896927+00:00
"""

import sqlalchemy as sa
import alembic.op as op


revision = '8527a0419ed6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # sessions table - stores browsing sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tag", sa.Text, nullable=False, unique=True),
        sa.Column("config", sa.JSON),
    )

    # pages table - stores pages visited during each browsing session
    # pages within a session should have unique content
    op.create_table(
        "pages",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("session_id", sa.BigInteger, sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("url_hash", sa.Text, index=True, nullable=False),
        sa.Column("content_path", sa.Text)
    )
    op.create_unique_constraint("pages_session_id_url_hash_uix", "pages", ["session_id", "url_hash"])

    # elements table - stores elements after preprocessing along with their context
    op.create_table(
        "elements",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("page_id", sa.BigInteger, sa.ForeignKey("pages.id"), nullable=False),
        sa.Column("is_root", sa.Boolean, index=True, server_default="t"),
        sa.Column("is_leaf", sa.Boolean, index=True, server_default="t"),
        sa.Column("parent_id", sa.BigInteger, sa.ForeignKey("elements.id")),  # handling element groups through parent reference
        sa.Column("xpath", sa.Text, nullable=False),
        sa.Column("element_position", sa.BigInteger, nullable=False),
        sa.Column("outer_html", sa.Text, nullable=False),
        sa.Column("context", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
    )
    op.create_unique_constraint("elements_page_id_parent_id_position_uix", "elements", ["page_id", "parent_id", "element_position"])

    # tasks table - stores tasks and subtasks throughout a session
    # session begins with a root task that the agent breaks into subtasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("session_id", sa.BigInteger, sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("is_root", sa.Boolean, index=True, server_default="f"),
        sa.Column("is_leaf", sa.Boolean, index=True, server_default="f"),
        sa.Column("parent_id", sa.BigInteger, sa.ForeignKey("tasks.id"), index=True),
        sa.Column("subtask_position", sa.BigInteger),
        sa.Column("context", sa.Text, nullable=False),
    )
    # only one root action per session so we can exclude session_id in uix
    op.create_unique_constraint("tasks_session_id_parent_id_subtask_position_uix", "tasks", ["session_id", "parent_id", "subtask_position"])

    # actions table - stores instances of interaction with specific browser elements on the page
    op.create_table(
        "actions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("task_id", sa.BigInteger, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("element_id", sa.BigInteger, sa.ForeignKey("elements.id"), index=True, nullable=False),
        sa.Column("new_page_id", sa.BigInteger, sa.ForeignKey("pages.id"), index=True),
        sa.Column("action_position", sa.BigInteger, nullable=False),
        sa.Column("metadata", sa.JSON),
        sa.Column("description", sa.Text),
    )
    op.create_unique_constraint("actions_task_id_action_position_uix", "actions", ["task_id", "action_position"])

    # filtered_elements table - tracks which page elements remain after filtering
    op.create_table(
        "filtered_elements",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("task_id", sa.BigInteger, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("element_id", sa.BigInteger, sa.ForeignKey("elements.id"), index=True, nullable=False),
    )
    op.create_unique_constraint("filtered_elements_task_id_element_id_uix", "filtered_elements", ["task_id", "element_id"])


def downgrade():
    pass
