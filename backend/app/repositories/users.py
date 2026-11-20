from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_or_create_default(self, timezone: str = "Asia/Jakarta") -> User:
        """The MVP is single-user: the first user row is the owner."""
        user = self.session.scalars(select(User).order_by(User.id).limit(1)).first()
        if user is None:
            user = User(timezone=timezone)
            self.session.add(user)
            self.session.flush()
        return user
