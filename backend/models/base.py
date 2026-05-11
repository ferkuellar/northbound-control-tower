from sqlalchemy.orm import Mapped, mapped_column

from core.database import TimestampMixin


class IntegerPrimaryKeyMixin:
    id: Mapped[int] = mapped_column(primary_key=True, index=True)


class BaseModelMixin(IntegerPrimaryKeyMixin, TimestampMixin):
    pass
