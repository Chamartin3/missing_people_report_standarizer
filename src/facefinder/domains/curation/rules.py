from dataclasses import dataclass

from facefinder.constants.enums import ConfirmationLevel

VALID_LEVELS: frozenset[ConfirmationLevel] = frozenset(ConfirmationLevel)


@dataclass
class TransitionError(Exception):
    message: str


def check_transition(
    from_level: ConfirmationLevel,
    to_level: ConfirmationLevel,
    user_id: int | None,
) -> None:
    if to_level not in VALID_LEVELS:
        raise TransitionError(f"unknown level: {to_level}")

    if user_id is None and to_level != ConfirmationLevel.SUGGESTED:
        raise TransitionError("only a human may set level beyond 'suggested'")

    if to_level == from_level:
        return

    if to_level == ConfirmationLevel.DISPUTED:
        return

    if to_level == ConfirmationLevel.REJECTED:
        return

    if from_level == ConfirmationLevel.SUGGESTED and to_level == ConfirmationLevel.PROBABLE:
        return

    if from_level == ConfirmationLevel.PROBABLE and to_level == ConfirmationLevel.CONFIRMED:
        return

    raise TransitionError(f"illegal transition: {from_level} -> {to_level}")
