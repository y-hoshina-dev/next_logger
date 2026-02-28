from __future__ import annotations

from enum import Enum


class AppState(str, Enum):
    IDLE = "IDLE"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


_TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.IDLE: {AppState.READY},
    AppState.READY: {AppState.RUNNING, AppState.IDLE, AppState.ERROR},
    AppState.RUNNING: {AppState.PAUSED, AppState.STOPPING, AppState.ERROR},
    AppState.PAUSED: {AppState.RUNNING, AppState.STOPPING, AppState.ERROR},
    AppState.STOPPING: {AppState.IDLE, AppState.ERROR},
    AppState.ERROR: {AppState.READY, AppState.IDLE},
}


class InvalidTransitionError(RuntimeError):
    pass


class StateMachine:
    def __init__(self) -> None:
        self._state = AppState.IDLE

    @property
    def state(self) -> AppState:
        return self._state

    def can_transition(self, to_state: AppState) -> bool:
        return to_state in _TRANSITIONS[self._state]

    def transition(self, to_state: AppState) -> None:
        if not self.can_transition(to_state):
            raise InvalidTransitionError(f"Invalid transition: {self._state} -> {to_state}")
        self._state = to_state
