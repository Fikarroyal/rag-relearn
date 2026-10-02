"""Skema database (SQLAlchemy). Foreign key + index pada kolom pencarian utama."""

from __future__ import annotations
from datetime import datetime
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.db import Base

now = datetime.utcnow


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    document_id = Column(String(120), unique=True, index=True)
    family = Column(String(120), index=True)
    title = Column(String(200))
    version = Column(Integer, default=1)
    source = Column(String(255))
    created_at = Column(DateTime, default=now)
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True)
    document_pk = Column(Integer, ForeignKey("documents.id"), index=True)
    family = Column(String(120), index=True)
    version = Column(Integer)
    is_latest = Column(Boolean, default=False)
    content_hash = Column(String(40))
    created_at = Column(DateTime, default=now)
    document = relationship("Document", back_populates="versions")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True)
    chunk_id = Column(String(160), unique=True, index=True)
    document_pk = Column(Integer, ForeignKey("documents.id"), index=True)
    document_id = Column(String(120), index=True)
    family = Column(String(120), index=True)
    title = Column(String(200))
    version = Column(Integer)
    section = Column(String(255))
    page = Column(Integer)
    chunk_index = Column(Integer)
    source = Column(String(255))
    content = Column(Text)
    content_hash = Column(String(40), index=True)
    vector = Column(JSON)
    created_at = Column(DateTime, default=now)
    document = relationship("Document", back_populates="chunks")


class Query(Base):
    __tablename__ = "queries"
    id = Column(Integer, primary_key=True)
    request_id = Column(String(32), index=True)
    text = Column(Text)
    query_class = Column(String(40))
    model_version = Column(String(40), index=True)
    created_at = Column(DateTime, default=now, index=True)


class RetrievalResult(Base):
    __tablename__ = "retrieval_results"
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), index=True)
    chunk_id = Column(String(160), index=True)
    rank = Column(Integer)
    similarity = Column(Float)
    reranking_score = Column(Float)
    original_rank = Column(Integer)
    selected = Column(Boolean, default=False)


class RagEvaluation(Base):
    __tablename__ = "rag_evaluations"
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), index=True)
    answer = Column(Text)
    citations = Column(JSON)
    ground_truth = Column(Text)
    ground_truth_chunk = Column(String(160))
    user_feedback = Column(String(40))
    failure_type = Column(String(60), index=True)
    failure_reason = Column(Text)
    latency = Column(JSON)
    metrics = Column(JSON)
    model_version = Column(String(40), index=True)
    embedding_model = Column(String(80))
    reranker_version = Column(String(80))
    confidence_score = Column(Float)
    timestamp = Column(DateTime, default=now, index=True)
    query = relationship("Query")


class FailureCase(Base):
    __tablename__ = "failure_cases"
    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("rag_evaluations.id"), index=True)
    query_text = Column(Text)
    failure_type = Column(String(60), index=True)
    severity = Column(String(12), index=True)
    model_version = Column(String(40), index=True)
    retriever = Column(String(80))
    reranker = Column(String(80))
    similarity = Column(Float)
    ground_truth = Column(Text)
    status = Column(String(20), default="open", index=True)
    diagnosis = Column(JSON)
    created_at = Column(DateTime, default=now, index=True)
    evaluation = relationship("RagEvaluation")


class HardNegative(Base):
    __tablename__ = "hard_negatives"
    id = Column(Integer, primary_key=True)
    failure_id = Column(Integer, ForeignKey("failure_cases.id"), index=True, nullable=True)
    query = Column(Text)
    positive = Column(String(160), index=True)
    hard_negative = Column(String(160), index=True)
    similarity = Column(Float)
    negative_type = Column(String(30))
    reason = Column(String(255))
    confidence = Column(Float)
    quality_score = Column(Float)
    failure_type = Column(String(60))
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, default=now)


class TrainingDataset(Base):
    __tablename__ = "training_datasets"
    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    stats = Column(JSON)
    validation = Column(JSON)
    created_at = Column(DateTime, default=now)
    samples = relationship("TrainingSample", back_populates="dataset", cascade="all, delete-orphan")


class TrainingSample(Base):
    __tablename__ = "training_samples"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("training_datasets.id"), index=True)
    query = Column(Text)
    positive = Column(String(160))
    hard_negative = Column(String(160))
    reason = Column(String(255))
    failure_type = Column(String(60))
    split = Column(String(12), index=True)
    quality_score = Column(Float)
    dataset = relationship("TrainingDataset", back_populates="samples")


class Model(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True)
    description = Column(Text)
    versions = relationship("ModelVersion", back_populates="model")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("models.id"), index=True)
    version = Column(String(40), index=True)
    base_model = Column(String(120))
    embedding_model = Column(String(120))
    reranker = Column(String(120))
    weights = Column(JSON)
    config = Column(JSON)
    training_dataset_id = Column(Integer, ForeignKey("training_datasets.id"), nullable=True)
    trained_at = Column(DateTime, default=now)
    metrics = Column(JSON)
    status = Column(String(20), default="candidate", index=True)
    model = relationship("Model", back_populates="versions")


class AbTest(Base):
    __tablename__ = "ab_tests"
    id = Column(Integer, primary_key=True)
    model_a = Column(String(40))
    model_b = Column(String(40))
    dataset = Column(String(120))
    results = Column(JSON)
    created_at = Column(DateTime, default=now)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id = Column(Integer, primary_key=True)
    dataset = Column(String(120))
    model_version = Column(String(40), index=True)
    retriever = Column(String(80))
    reranker = Column(String(80))
    top_k = Column(Integer)
    metrics = Column(JSON)
    per_query = Column(JSON)
    status = Column(String(20), default="completed")
    created_at = Column(DateTime, default=now)


class TrainingJob(Base):
    __tablename__ = "training_jobs"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("training_datasets.id"), index=True)
    config = Column(JSON)
    status = Column(String(20), default="queued", index=True)
    history = Column(JSON, default=list)
    result = Column(JSON)
    model_version = Column(String(40))
    error = Column(Text)
    created_at = Column(DateTime, default=now)
    finished_at = Column(DateTime)


class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(Integer, primary_key=True)
    exp_id = Column(String(20), unique=True, index=True)
    baseline = Column(String(60))
    candidate = Column(String(60))
    dataset = Column(String(120))
    config = Column(JSON)
    metrics = Column(JSON)
    improvement = Column(JSON)
    status = Column(String(20), default="completed")
    created_at = Column(DateTime, default=now)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(60), unique=True, index=True)
    password_hash = Column(String(200))
    role = Column(String(20), default="viewer")


class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True)
    request_id = Column(String(32), index=True)
    method = Column(String(8))
    path = Column(String(200))
    status = Column(Integer)
    latency_ms = Column(Float)
    created_at = Column(DateTime, default=now, index=True)
