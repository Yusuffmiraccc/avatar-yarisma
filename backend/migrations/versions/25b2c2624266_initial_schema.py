"""Remove obsolete product tracking schema.

Revision ID: 25b2c2624266
Revises: 2d87a7f6bfdf
"""

from alembic import op
import sqlalchemy as sa

revision = "25b2c2624266"
down_revision = "2d87a7f6bfdf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("unit_conversions")
    op.drop_column("products", "is_lot_tracked")


def downgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "is_lot_tracked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "unit_conversions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("from_unit_code", sa.String(length=20), nullable=False),
        sa.Column("to_unit_code", sa.String(length=20), nullable=False),
        sa.Column("factor", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )