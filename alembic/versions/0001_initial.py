"""initial migration

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("scanner", "partner", "manual", name="leadsource"),
            nullable=False,
        ),
        sa.Column(
            "stage",
            sa.Enum("new", "contacted", "qualified", "transferred", "lost", name="coldstage"),
            nullable=False,
        ),
        sa.Column(
            "business_domain",
            sa.Enum("first", "second", "third", name="businessdomain"),
            nullable=True,
        ),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("ai_recommendation", sa.String(length=64), nullable=True),
        sa.Column("ai_reason", sa.Text(), nullable=True),
        sa.Column("ai_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leads_id"), "leads", ["id"], unique=False)

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("new", "kyc", "agreement", "paid", "lost", name="salestage"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id"),
    )
    op.create_index(op.f("ix_sales_id"), "sales", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_id"), table_name="sales")
    op.drop_table("sales")
    op.drop_index(op.f("ix_leads_id"), table_name="leads")
    op.drop_table("leads")
    op.execute("DROP TYPE IF EXISTS salestage")
    op.execute("DROP TYPE IF EXISTS coldstage")
    op.execute("DROP TYPE IF EXISTS businessdomain")
    op.execute("DROP TYPE IF EXISTS leadsource")
