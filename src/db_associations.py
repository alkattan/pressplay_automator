from sqlalchemy import Column, ForeignKey, Integer, Table, UniqueConstraint

from src.database.connection import Base


# Association table for many-to-many relationship between CSL and Locale
csl_locale = Table(
    'csl_locale',
    Base.metadata,
    Column('csl_id', Integer, ForeignKey('csls.id'), nullable=False),
    Column('locale_id', Integer, ForeignKey('locales.id'), nullable=False),
    UniqueConstraint("locale_id", "csl_id", name="uq_csl_locale")
)

users_organizations_association = Table(
    "users_organizations_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("organization_id", Integer, ForeignKey("organizations.id")),
    UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
)
