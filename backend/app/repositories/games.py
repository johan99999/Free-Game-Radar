from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Game
from app.models.enums import Platform


class GameRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, game_id: int) -> Game | None:
        return self.session.get(Game, game_id)

    def get_by_platform_id(self, platform: Platform, platform_game_id: str) -> Game | None:
        stmt = select(Game).where(
            Game.platform == platform, Game.platform_game_id == platform_game_id
        )
        return self.session.scalars(stmt).first()

    def upsert(
        self,
        platform: Platform,
        platform_game_id: str,
        title: str,
        store_url: str | None = None,
        image_url: str | None = None,
    ) -> tuple[Game, bool]:
        """Insert or update by (platform, platform_game_id). Returns (game, created)."""
        game = self.get_by_platform_id(platform, platform_game_id)
        if game is None:
            game = Game(
                platform=platform,
                platform_game_id=platform_game_id,
                title=title,
                store_url=store_url,
                image_url=image_url,
            )
            self.session.add(game)
            self.session.flush()
            return game, True
        game.title = title
        if store_url is not None:
            game.store_url = store_url
        if image_url is not None:
            game.image_url = image_url
        self.session.flush()
        return game, False

    def list_games(
        self, platform: Platform | None = None, limit: int = 50, offset: int = 0
    ) -> list[Game]:
        stmt = select(Game).order_by(Game.id).limit(limit).offset(offset)
        if platform is not None:
            stmt = stmt.where(Game.platform == platform)
        return list(self.session.scalars(stmt))

    def delete(self, game_id: int) -> bool:
        game = self.get(game_id)
        if game is None:
            return False
        self.session.delete(game)
        self.session.flush()
        return True
