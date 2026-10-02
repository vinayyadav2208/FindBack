"""SQLAlchemy models for FindBack.

Existing tables (`users`, `lost_items`, `found_items`) keep their original
columns; new columns are added non-destructively at runtime by
`app.migrations.ensure_schema`, so existing development data is preserved.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

from app import constants as C

Base = declarative_base()


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(
        String(20),
        nullable=False,
        default=C.ROLE_USER,
        server_default=C.ROLE_USER,
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        server_default=func.current_timestamp(),
    )

    lost_items = relationship("LostItem", back_populates="user")
    found_items = relationship("FoundItem", back_populates="user")
    donations = relationship("Donation", back_populates="user")
    claims = relationship("Claim", back_populates="claimant", foreign_keys="Claim.claimant_id")
    notifications = relationship("Notification", back_populates="user")
    reports = relationship("Report", back_populates="reporter")

    @property
    def is_admin(self) -> bool:
        return self.role == C.ROLE_ADMIN


class LostItem(Base):
    __tablename__ = "lost_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    category = Column(
        String(50), nullable=False, default=C.DEFAULT_CATEGORY, server_default=C.DEFAULT_CATEGORY
    )
    location = Column(String(100), nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(
        String(20), nullable=False, default=C.LOST_ACTIVE, server_default=C.LOST_ACTIVE, index=True
    )
    images = Column(JSON, nullable=True)  # list of stored image URLs/paths
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp(), index=True
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        server_default=func.current_timestamp(),
    )

    user = relationship("User", back_populates="lost_items")


class FoundItem(Base):
    __tablename__ = "found_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    category = Column(
        String(50), nullable=False, default=C.DEFAULT_CATEGORY, server_default=C.DEFAULT_CATEGORY
    )
    location = Column(String(100), nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(
        String(20), nullable=False, default=C.FOUND_ACTIVE, server_default=C.FOUND_ACTIVE, index=True
    )
    images = Column(JSON, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp(), index=True
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        server_default=func.current_timestamp(),
    )

    user = relationship("User", back_populates="found_items")


class Donation(Base):
    """Free give-away listings (MASTER_README §23)."""

    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    category = Column(
        String(50), nullable=False, default=C.DEFAULT_CATEGORY, server_default=C.DEFAULT_CATEGORY
    )
    condition = Column(
        String(20), nullable=False, default=C.CONDITION_GOOD, server_default=C.CONDITION_GOOD
    )
    location = Column(String(100), nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    images = Column(JSON, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default=C.DONATION_AVAILABLE,
        server_default=C.DONATION_AVAILABLE,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp(), index=True
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        server_default=func.current_timestamp(),
    )

    user = relationship("User", back_populates="donations")


class Claim(Base):
    """Ownership claims for found items, plus donation requests (§25)."""

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(20), nullable=False, index=True)   # FOUND_ITEM | DONATION | LOST_ITEM
    item_id = Column(Integer, nullable=False, index=True)
    claimant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=True)
    # Private verification answers - never exposed on public listings (§70)
    verification_answers = Column(JSON, nullable=True)
    status = Column(
        String(20), nullable=False, default=C.CLAIM_PENDING, server_default=C.CLAIM_PENDING, index=True
    )
    review_note = Column(Text, nullable=True)   # owner/admin note when approving or rejecting
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        server_default=func.current_timestamp(),
    )

    claimant = relationship("User", back_populates="claims", foreign_keys=[claimant_id])


class Match(Base):
    """Potential lost/found matches produced by the AI matching service (§30)."""

    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("lost_item_id", "found_item_id", name="uq_matches_pair"),
    )

    id = Column(Integer, primary_key=True, index=True)
    lost_item_id = Column(Integer, ForeignKey("lost_items.id"), nullable=False, index=True)
    found_item_id = Column(Integer, ForeignKey("found_items.id"), nullable=False, index=True)
    text_score = Column(Float, default=0.0, server_default="0")
    image_score = Column(Float, default=0.0, server_default="0")
    location_score = Column(Float, default=0.0, server_default="0")
    category_score = Column(Float, default=0.0, server_default="0")
    combined_score = Column(Float, default=0.0, server_default="0", index=True)
    # Human-readable reasons ("similar category, similar location") - §34
    explanation = Column(JSON, nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default=C.MATCH_POTENTIAL,
        server_default=C.MATCH_POTENTIAL,
        index=True,
    )
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp()
    )

    lost_item = relationship("LostItem")
    found_item = relationship("FoundItem")


class Message(Base):
    """Direct conversation between the two parties of a match or a claim.

    Lets the person who lost an item and the person who found it (or a donor
    and someone who requested their donation) talk directly to arrange a
    handover instead of relying on out-of-band contact. A message belongs to
    exactly one thread: `match_id` XOR `claim_id`. Only the parties (and
    admins) can read a thread; `is_read` tracks whether the *recipient* has
    read the message.
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp(), index=True
    )

    match = relationship("Match")
    claim = relationship("Claim")
    sender = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(30), nullable=False, default=C.NOTIF_SYSTEM, server_default=C.NOTIF_SYSTEM)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    # Optional deep-link target: what this notification is ABOUT (MATCH/CLAIM/
    # REPORT/USER + id) so the UI can navigate to the exact thread or record.
    related_type = Column(String(30), nullable=True)
    related_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp(), index=True
    )

    user = relationship("User", back_populates="notifications")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_type = Column(String(30), nullable=False, index=True)
    target_id = Column(Integer, nullable=False, index=True)
    reason = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(20), nullable=False, default=C.REPORT_OPEN, server_default=C.REPORT_OPEN, index=True
    )
    created_at = Column(
        DateTime, nullable=False, default=_now, server_default=func.current_timestamp()
    )

    reporter = relationship("User", back_populates="reports")
