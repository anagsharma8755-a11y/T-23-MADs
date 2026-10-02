import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Numeric, Text, JSON, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now(): return datetime.now(timezone.utc)
class Role(str, enum.Enum): analyst="analyst"; supervisor="supervisor"
class ReviewStatus(str, enum.Enum): unreviewed="unreviewed"; under_review="under_review"; confirmed="confirmed_suspicious"; cleared="cleared"

class Workspace(Base):
    __tablename__="workspaces"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(120)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class User(Base):
    __tablename__="users"; id: Mapped[int]=mapped_column(primary_key=True); workspace_id: Mapped[int]=mapped_column(ForeignKey("workspaces.id"),index=True); email: Mapped[str]=mapped_column(String(255),unique=True,index=True); name: Mapped[str]=mapped_column(String(120)); password_hash: Mapped[str]=mapped_column(String(255)); role: Mapped[str]=mapped_column(String(20),default=Role.analyst.value); active: Mapped[bool]=mapped_column(Boolean,default=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Session(Base):
    __tablename__="sessions"; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True); token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True); csrf_hash: Mapped[str]=mapped_column(String(64)); expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class LoginAttempt(Base):
    __tablename__="login_attempts"; id: Mapped[int]=mapped_column(primary_key=True); key: Mapped[str]=mapped_column(String(255),index=True); attempted_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True); success: Mapped[bool]=mapped_column(Boolean,default=False)
class Dataset(Base):
    __tablename__="datasets"; id: Mapped[int]=mapped_column(primary_key=True); workspace_id: Mapped[int]=mapped_column(ForeignKey("workspaces.id"),index=True); name: Mapped[str]=mapped_column(String(180)); filename: Mapped[str]=mapped_column(String(255)); account_filename: Mapped[str|None]=mapped_column(String(255),nullable=True); import_status: Mapped[str]=mapped_column(String(30),default="completed"); transaction_count: Mapped[int]=mapped_column(Integer,default=0); account_count: Mapped[int]=mapped_column(Integer,default=0); uploaded_by: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
class Account(Base):
    __tablename__="accounts"; id: Mapped[int]=mapped_column(primary_key=True); dataset_id: Mapped[int]=mapped_column(ForeignKey("datasets.id",ondelete="CASCADE"),index=True); account_id: Mapped[str]=mapped_column(String(180)); created_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); opening_balance: Mapped[float|None]=mapped_column(Numeric(20,4),nullable=True); device_id: Mapped[str|None]=mapped_column(String(180),nullable=True); ip_address: Mapped[str|None]=mapped_column(String(80),nullable=True); kyc_group_id: Mapped[str|None]=mapped_column(String(180),nullable=True); __table_args__=(UniqueConstraint("dataset_id","account_id"),)
class Transaction(Base):
    __tablename__="transactions"; id: Mapped[int]=mapped_column(primary_key=True); dataset_id: Mapped[int]=mapped_column(ForeignKey("datasets.id",ondelete="CASCADE"),index=True); transaction_id: Mapped[str]=mapped_column(String(180)); timestamp: Mapped[datetime]=mapped_column(DateTime(timezone=True)); sender_account: Mapped[str]=mapped_column(String(180)); receiver_account: Mapped[str]=mapped_column(String(180)); amount: Mapped[float]=mapped_column(Numeric(20,4)); currency: Mapped[str]=mapped_column(String(12)); sender_device_id: Mapped[str|None]=mapped_column(String(180),nullable=True); receiver_device_id: Mapped[str|None]=mapped_column(String(180),nullable=True); sender_ip: Mapped[str|None]=mapped_column(String(80),nullable=True); receiver_ip: Mapped[str|None]=mapped_column(String(80),nullable=True); __table_args__=(UniqueConstraint("dataset_id","transaction_id"),Index("ix_tx_dataset_sender_time","dataset_id","sender_account","timestamp"),Index("ix_tx_dataset_receiver_time","dataset_id","receiver_account","timestamp"))
class DetectionSettings(Base):
    __tablename__="detection_settings"; id: Mapped[int]=mapped_column(primary_key=True); workspace_id: Mapped[int]=mapped_column(ForeignKey("workspaces.id"),index=True); version: Mapped[int]=mapped_column(Integer); config: Mapped[dict]=mapped_column(JSON); created_by: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); __table_args__=(UniqueConstraint("workspace_id","version"),)
class AnalysisRun(Base):
    __tablename__="analysis_runs"; id: Mapped[int]=mapped_column(primary_key=True); dataset_id: Mapped[int]=mapped_column(ForeignKey("datasets.id",ondelete="CASCADE"),index=True); settings_id: Mapped[int]=mapped_column(ForeignKey("detection_settings.id")); status: Mapped[str]=mapped_column(String(30),default="queued"); progress: Mapped[int]=mapped_column(Integer,default=0); error: Mapped[str|None]=mapped_column(Text,nullable=True); created_by: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
class Finding(Base):
    __tablename__="findings"; id: Mapped[int]=mapped_column(primary_key=True); run_id: Mapped[int]=mapped_column(ForeignKey("analysis_runs.id",ondelete="CASCADE"),index=True); detector: Mapped[str]=mapped_column(String(80),index=True); detector_version: Mapped[str]=mapped_column(String(20)); currency: Mapped[str|None]=mapped_column(String(12),nullable=True); account_ids: Mapped[list]=mapped_column(JSON); transaction_ids: Mapped[list]=mapped_column(JSON); evidence: Mapped[dict]=mapped_column(JSON); reason: Mapped[str]=mapped_column(Text); limitations: Mapped[list]=mapped_column(JSON); contribution: Mapped[int]=mapped_column(Integer); fingerprint: Mapped[str]=mapped_column(String(64)); __table_args__=(UniqueConstraint("run_id","fingerprint"),)
class AccountScore(Base):
    __tablename__="account_scores"; id: Mapped[int]=mapped_column(primary_key=True); run_id: Mapped[int]=mapped_column(ForeignKey("analysis_runs.id",ondelete="CASCADE"),index=True); account_id: Mapped[str]=mapped_column(String(180),index=True); score: Mapped[int]=mapped_column(Integer); severity: Mapped[str]=mapped_column(String(20)); breakdown: Mapped[dict]=mapped_column(JSON); finding_ids: Mapped[list]=mapped_column(JSON); review_status: Mapped[str]=mapped_column(String(30),default=ReviewStatus.unreviewed.value); __table_args__=(UniqueConstraint("run_id","account_id"),)
class Decision(Base):
    __tablename__="decisions"; id: Mapped[int]=mapped_column(primary_key=True); score_id: Mapped[int]=mapped_column(ForeignKey("account_scores.id",ondelete="CASCADE"),index=True); status: Mapped[str]=mapped_column(String(30)); note: Mapped[str|None]=mapped_column(Text,nullable=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AuditEvent(Base):
    __tablename__="audit_events"; id: Mapped[int]=mapped_column(primary_key=True); workspace_id: Mapped[int]=mapped_column(ForeignKey("workspaces.id"),index=True); user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True); action: Mapped[str]=mapped_column(String(100),index=True); target_type: Mapped[str]=mapped_column(String(80)); target_id: Mapped[str]=mapped_column(String(180)); details: Mapped[dict]=mapped_column(JSON,default=dict); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)

class BlockchainDataset(Base):
    __tablename__="blockchain_datasets"
    id: Mapped[int]=mapped_column(primary_key=True)
    workspace_id: Mapped[int]=mapped_column(ForeignKey("workspaces.id"),index=True)
    name: Mapped[str]=mapped_column(String(180))
    source_url: Mapped[str]=mapped_column(String(500))
    schema_version: Mapped[str]=mapped_column(String(40))
    subset_method: Mapped[str]=mapped_column(Text)
    manifest_hash: Mapped[str]=mapped_column(String(64),index=True)
    source_files: Mapped[dict]=mapped_column(JSON)
    capabilities: Mapped[dict]=mapped_column(JSON)
    wallet_count: Mapped[int]=mapped_column(Integer,default=0)
    transaction_node_count: Mapped[int]=mapped_column(Integer,default=0)
    relationship_count: Mapped[int]=mapped_column(Integer,default=0)
    imported_by: Mapped[int]=mapped_column(ForeignKey("users.id"))
    imported_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
    __table_args__=(UniqueConstraint("workspace_id","manifest_hash"),)

class BlockchainWallet(Base):
    __tablename__="blockchain_wallets"
    id: Mapped[int]=mapped_column(primary_key=True)
    dataset_id: Mapped[int]=mapped_column(ForeignKey("blockchain_datasets.id",ondelete="CASCADE"),index=True)
    address: Mapped[str]=mapped_column(String(180),index=True)
    time_step: Mapped[int|None]=mapped_column(Integer,nullable=True,index=True)
    features: Mapped[dict]=mapped_column(JSON,default=dict)
    __table_args__=(UniqueConstraint("dataset_id","address"),)

class BlockchainTransactionNode(Base):
    __tablename__="blockchain_transaction_nodes"
    id: Mapped[int]=mapped_column(primary_key=True)
    dataset_id: Mapped[int]=mapped_column(ForeignKey("blockchain_datasets.id",ondelete="CASCADE"),index=True)
    tx_id: Mapped[str]=mapped_column(String(180),index=True)
    time_step: Mapped[int|None]=mapped_column(Integer,nullable=True,index=True)
    features: Mapped[dict]=mapped_column(JSON,default=dict)
    __table_args__=(UniqueConstraint("dataset_id","tx_id"),)

class BlockchainNodeFeature(Base):
    __tablename__="blockchain_node_features"
    id: Mapped[int]=mapped_column(primary_key=True)
    dataset_id: Mapped[int]=mapped_column(ForeignKey("blockchain_datasets.id",ondelete="CASCADE"),index=True)
    node_type: Mapped[str]=mapped_column(String(20),index=True)
    node_id: Mapped[str]=mapped_column(String(180),index=True)
    time_step: Mapped[int|None]=mapped_column(Integer,nullable=True,index=True)
    observation_index: Mapped[int]=mapped_column(Integer,default=0)
    features: Mapped[dict]=mapped_column(JSON)
    __table_args__=(UniqueConstraint("dataset_id","node_type","node_id","time_step","observation_index"),)

class BlockchainRelationship(Base):
    __tablename__="blockchain_relationships"
    id: Mapped[int]=mapped_column(primary_key=True)
    dataset_id: Mapped[int]=mapped_column(ForeignKey("blockchain_datasets.id",ondelete="CASCADE"),index=True)
    relationship_type: Mapped[str]=mapped_column(String(40),index=True)
    source_type: Mapped[str]=mapped_column(String(20))
    source_id: Mapped[str]=mapped_column(String(180),index=True)
    target_type: Mapped[str]=mapped_column(String(20))
    target_id: Mapped[str]=mapped_column(String(180),index=True)
    __table_args__=(UniqueConstraint("dataset_id","relationship_type","source_id","target_id"),)

class BlockchainReferenceLabel(Base):
    __tablename__="blockchain_reference_labels"
    id: Mapped[int]=mapped_column(primary_key=True)
    dataset_id: Mapped[int]=mapped_column(ForeignKey("blockchain_datasets.id",ondelete="CASCADE"),index=True)
    node_type: Mapped[str]=mapped_column(String(20),index=True)
    node_id: Mapped[str]=mapped_column(String(180),index=True)
    label_code: Mapped[int]=mapped_column(Integer)
    label_name: Mapped[str]=mapped_column(String(20))
    __table_args__=(UniqueConstraint("dataset_id","node_type","node_id"),)

class BlockchainWalletScore(Base):
    __tablename__="blockchain_wallet_scores"
    id: Mapped[int]=mapped_column(primary_key=True)
    dataset_id: Mapped[int]=mapped_column(ForeignKey("blockchain_datasets.id",ondelete="CASCADE"),index=True)
    address: Mapped[str]=mapped_column(String(180),index=True)
    score: Mapped[int]=mapped_column(Integer)
    severity: Mapped[str]=mapped_column(String(20))
    breakdown: Mapped[dict]=mapped_column(JSON)
    reasons: Mapped[list]=mapped_column(JSON)
    evidence: Mapped[dict]=mapped_column(JSON)
    review_status: Mapped[str]=mapped_column(String(30),default=ReviewStatus.unreviewed.value)
    __table_args__=(UniqueConstraint("dataset_id","address"),)

class BlockchainDecision(Base):
    __tablename__="blockchain_decisions"
    id: Mapped[int]=mapped_column(primary_key=True)
    score_id: Mapped[int]=mapped_column(ForeignKey("blockchain_wallet_scores.id",ondelete="CASCADE"),index=True)
    status: Mapped[str]=mapped_column(String(30))
    note: Mapped[str|None]=mapped_column(Text,nullable=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
