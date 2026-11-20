import enum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import MappedColumn, mapped_column


def enum_column(enum_cls: type[enum.Enum], **kwargs: Any) -> MappedColumn[Any]:
    """Enum stored as a VARCHAR holding the member name (portable, no native enum type)."""
    return mapped_column(sa.Enum(enum_cls, native_enum=False, length=32), **kwargs)
