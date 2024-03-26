from pathlib import Path
from typing import List

from action import *
from board import GameBoard, RESOURCES
from queue import LifoQueue


def _make_action_sequence(state: dict) -> List[Action]:
    # If there is no parent specified in the state, then it is an initial action.
    if 'parent' not in state:
        return []

    # Move back to the parent state, and read the action sequence until that state.
    parental_state, parent_action = state['parent']
    # Append the required action to reach the current state at the end of the parent's action list.
    return _make_action_sequence(parental_state) + [parent_action]


class Agent:  # Do not change the name of this class!
    """
    An agent class with DFS, different ordering of actions
    """
    def search_for_longest_route(self, board: GameBoard) -> List[Action]:
        """
        This algorithm search for an action sequence that makes the longest trading route at the end of the game.
        If there's no solution, then return an empty list.

        :param board: Game board to manipulate
        :return: List of actions
        """
        # Set up frontiers as LIFO Queue
        frontier = LifoQueue()
        # Read initial state
        initial_state = board.get_initial_state()
        frontier.put(initial_state)
        reached = [initial_state['state_id']]

        # Until the frontier is nonempty,
        while not frontier.empty():
            # Read a state to search further
            state = frontier.get()
            board.set_to_state(state)

            # If it is the game end, then read action sequences by back-tracing the actions.
            if board.is_game_end():
                return _make_action_sequence(state)

            # Build applicable actions
            # 5) TRADE
            possible_actions = [TRADE(r, r2)
                                 for r in RESOURCES
                                 if board.get_trading_rate(r) > 0
                                 for r2 in RESOURCES
                                 if r != r2]
            # 4) VILLAGE
            possible_actions += [VILLAGE(v)
                                 for v in board.get_applicable_villages()]
            # 3) PASS
            possible_actions += [PASS()]
            # 2) ROAD
            possible_actions += [ROAD(road)
                                 for road in board.get_applicable_roads()]
            # 1) UPGRADE
            possible_actions += [UPGRADE(v)
                                 for v in board.get_applicable_cities()]

            # Expand next states
            for action in possible_actions:
                child = board.simulate_action(state, action)

                # If the next state is already reached, then pass to the next action
                if child['state_id'] in reached:
                    continue

                # Add parent information to the next state
                child['parent'] = (state, action)
                frontier.put(child)
                reached.append(child['state_id'])

        # Return empty list if search fails.
        return []
