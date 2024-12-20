from datetime import datetime
from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.connection import Base
from src.db_associations import users_organizations_association



class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)

    email: Mapped[str] = mapped_column(String(128), nullable=False)
    given_name: Mapped[str] = mapped_column(String(128), nullable=False)
    family_name: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sub: Mapped[str] = mapped_column(String(128), nullable=False)
    picture: Mapped[str] = mapped_column(String(256), nullable=False)

    organizations: Mapped[List["OrganizationModel"]] = relationship(
        "OrganizationModel",
        secondary=users_organizations_association,
        back_populates="users",
    )

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
