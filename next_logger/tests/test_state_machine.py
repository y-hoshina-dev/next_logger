import unittest

from next_logger.domain import AppState, InvalidTransitionError, StateMachine


class TestStateMachine(unittest.TestCase):
    def test_valid_transitions(self) -> None:
        sm = StateMachine()
        self.assertEqual(sm.state, AppState.IDLE)

        sm.transition(AppState.READY)
        sm.transition(AppState.RUNNING)
        sm.transition(AppState.PAUSED)
        sm.transition(AppState.RUNNING)
        sm.transition(AppState.STOPPING)
        sm.transition(AppState.IDLE)

        self.assertEqual(sm.state, AppState.IDLE)

    def test_invalid_transition_raises(self) -> None:
        sm = StateMachine()
        with self.assertRaises(InvalidTransitionError):
            sm.transition(AppState.RUNNING)


if __name__ == "__main__":
    unittest.main()
