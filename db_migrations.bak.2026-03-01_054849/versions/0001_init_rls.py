from alembic import op
import sqlalchemy as sa

revision = "0001_init_rls"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('dispatcher','manager')", name="ck_users_role"),
    )

    # если дальше в твоей системе в 0001 создаются другие таблицы — оставь их как есть,
    # но ВЕЗДЕ где было Enum(user_role) используй String + CHECK/валидацию на уровне приложения.


def downgrade() -> None:
    op.drop_table("users")
