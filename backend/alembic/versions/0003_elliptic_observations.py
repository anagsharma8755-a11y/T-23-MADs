"""preserve repeated Elliptic++ feature observations

Revision ID: 0003_elliptic_observations
Revises: 0002_ellipticpp
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_elliptic_observations"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    if "blockchain_node_features" not in inspector.get_table_names():
        return
    if "observation_index" in {column["name"] for column in inspector.get_columns("blockchain_node_features")}:
        return
    # A named convention allows Alembic's SQLite batch recreation to address
    # the unnamed unique constraint created by early development builds.
    naming={"uq":"uq_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table("blockchain_node_features",naming_convention=naming) as batch:
        batch.drop_constraint("uq_blockchain_node_features_dataset_id",type_="unique")
        batch.add_column(sa.Column("observation_index",sa.Integer(),nullable=False,server_default="0"))
        batch.create_unique_constraint("uq_blockchain_node_features_observation",["dataset_id","node_type","node_id","time_step","observation_index"])

def downgrade():
    with op.batch_alter_table("blockchain_node_features") as batch:
        batch.drop_constraint("uq_blockchain_node_features_observation",type_="unique")
        batch.drop_column("observation_index")
        batch.create_unique_constraint("uq_blockchain_node_features",["dataset_id","node_type","node_id","time_step"])
