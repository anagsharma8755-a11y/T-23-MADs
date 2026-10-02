"""Elliptic++ blockchain domain tables"""
from alembic import op
from app.db import Base
from app import models  # noqa: F401

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    for name in ["blockchain_decisions","blockchain_wallet_scores","blockchain_reference_labels","blockchain_relationships","blockchain_node_features","blockchain_transaction_nodes","blockchain_wallets","blockchain_datasets"]:
        op.drop_table(name)
