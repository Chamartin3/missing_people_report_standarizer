from facefinder.constants.types import UserData


class BaseService:
    """Shared machinery for service classes.

    Carries the acting user so operations don't re-thread `user_id` through
    every call, and centralizes the "is anyone authenticated" check that the
    API used to repeat per-route.
    """

    def __init__(self, actor: UserData | None = None) -> None:
        self.actor = actor

    @property
    def actor_id(self) -> int | None:
        return self.actor.id if self.actor else None

    def require_actor(self) -> int:
        if self.actor_id is None:
            raise PermissionError("authentication required")
        return self.actor_id
