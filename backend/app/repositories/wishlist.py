from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WishlistItem


class WishlistRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int, game_id: int) -> WishlistItem | None:
        stmt = select(WishlistItem).where(
            WishlistItem.user_id == user_id, WishlistItem.game_id == game_id
        )
        return self.session.scalars(stmt).first()

    def add(
        self,
        user_id: int,
        game_id: int,
        steam_app_id: str | None = None,
        target_price_minor: int | None = None,
    ) -> tuple[WishlistItem, bool]:
        """Idempotent. Returns (item, created)."""
        item = self.get(user_id, game_id)
        if item is not None:
            return item, False
        item = WishlistItem(
            user_id=user_id,
            game_id=game_id,
            steam_app_id=steam_app_id,
            target_price_minor=target_price_minor,
        )
        self.session.add(item)
        self.session.flush()
        return item, True

    def list_for_user(self, user_id: int) -> list[WishlistItem]:
        stmt = select(WishlistItem).where(WishlistItem.user_id == user_id).order_by(WishlistItem.id)
        return list(self.session.scalars(stmt))

    def set_target_price(self, item: WishlistItem, target_price_minor: int | None) -> None:
        item.target_price_minor = target_price_minor
        self.session.flush()

    def remove(self, user_id: int, game_id: int) -> bool:
        item = self.get(user_id, game_id)
        if item is None:
            return False
        self.session.delete(item)
        self.session.flush()
        return True
