from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.connection import Base
from src.db_associations import users_organizations_association
from src.modules.user.models import UserModel


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    name: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(default=False)

    # Auth0 Organization fields
    auth0_org_id: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    org_name: Mapped[Optional[str]] = mapped_column(String(32), default=None)

    users: Mapped[List["UserModel"]] = relationship(
        "UserModel",
        secondary=users_organizations_association,
        back_populates="organizations",
    )

    publishers = relationship("PublisherModel", back_populates="organization")
