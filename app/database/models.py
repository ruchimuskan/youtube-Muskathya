from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class VideoPrivacy(str, enum.Enum):
    private = "private"
    unlisted = "unlisted"
    public = "public"


class ChannelConnection(Base):
    __tablename__ = "channel_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True)
    channel_title: Mapped[str] = mapped_column(String(255))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StoryProject(Base):
    __tablename__ = "story_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    language: Mapped[str] = mapped_column(String(8))
    genre: Mapped[str] = mapped_column(String(64))
    target_duration_sec: Mapped[int] = mapped_column(Integer)
    is_short: Mapped[bool] = mapped_column(Boolean, default=False)
    story_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    lessons_applied: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    videos: Mapped[list[VideoAsset]] = relationship(back_populates="story")


class VideoAsset(Base):
    __tablename__ = "video_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int | None] = mapped_column(ForeignKey("story_projects.id"), nullable=True)
    local_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    aspect_ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    qc_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    qc_report: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    story: Mapped[StoryProject | None] = relationship(back_populates="videos")
    youtube_uploads: Mapped[list[YouTubeUpload]] = relationship(back_populates="video_asset")
    performance_snapshots: Mapped[list[VideoPerformanceSnapshot]] = relationship(back_populates="video")


class YouTubeUpload(Base):
    __tablename__ = "youtube_uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_asset_id: Mapped[int] = mapped_column(ForeignKey("video_assets.id"))
    youtube_video_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON)
    category_id: Mapped[str] = mapped_column(String(8), default="24")
    privacy: Mapped[VideoPrivacy] = mapped_column(Enum(VideoPrivacy), default=VideoPrivacy.private)
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    upload_status: Mapped[str] = mapped_column(String(32), default="pending")
    thumbnail_status: Mapped[str] = mapped_column(String(32), default="pending")
    api_errors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video_asset: Mapped[VideoAsset] = relationship(back_populates="youtube_uploads")
    seo_meta: Mapped[SEOMetadata | None] = relationship(back_populates="upload", uselist=False)


class SEOMetadata(Base):
    __tablename__ = "seo_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("youtube_uploads.id"), unique=True)
    main_topic: Mapped[str] = mapped_column(String(255))
    keywords: Mapped[list[str]] = mapped_column(JSON)
    title_variations: Mapped[list[str]] = mapped_column(JSON)
    recommended_title: Mapped[str] = mapped_column(String(100))
    hashtags: Mapped[list[str]] = mapped_column(JSON)
    chapters: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    search_experiments: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    upload: Mapped[YouTubeUpload] = relationship(back_populates="seo_meta")


class VideoPerformanceSnapshot(Base):
    __tablename__ = "video_performance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_asset_id: Mapped[int] = mapped_column(ForeignKey("video_assets.id"))
    snapshot_label: Mapped[str] = mapped_column(String(16))  # 24h, 7d, 28d
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON)

    video: Mapped[VideoAsset] = relationship(back_populates="performance_snapshots")


class ProductionQualityCheck(Base):
    __tablename__ = "production_quality_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_asset_id: Mapped[int] = mapped_column(ForeignKey("video_assets.id"))
    check_type: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool] = mapped_column(Boolean)
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MistakeReport(Base):
    __tablename__ = "mistake_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_asset_id: Mapped[int] = mapped_column(ForeignKey("video_assets.id"))
    report_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearningRecord(Base):
    __tablename__ = "learning_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(64))
    lesson: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    applied_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    tokens_estimated: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AutomationJob(Base):
    __tablename__ = "automation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
