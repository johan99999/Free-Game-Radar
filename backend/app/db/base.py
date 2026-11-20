from datetime import datetime

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from app.db.types import UTCDateTime

# Predictable names for constraints so migrations are stable. Unique constraints and
# indexes are always named explicitly in the models.
NAMING_CONVENTION = {
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: UTCDateTime}
