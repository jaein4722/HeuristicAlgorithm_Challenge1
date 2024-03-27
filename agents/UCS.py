from pathlib import Path
from typing import List

from action import *
from board import GameBoard, RESOURCES
from queue import LifoQueue, PriorityQueue, Queue


def _make_action_sequence(state: dict) -> List[Action]:
    # If there is no parent specified in the state, then it is an initial action.
    if 'parent' not in state:
        return []

    # Move back to the parent state, and read the action sequence until that state.
    parental_state, parent_action, parent_cost = state['parent']
    # Append the required action to reach the current state at the end of the parent's action list.
    return _make_action_sequence(parental_state) + [parent_action]

def _pathCost(state: dict) -> int:
    if 'parent' not in state:
        return 0
    
    parental_state, parent_action, parent_cost = state['parent']
    return _pathCost(parental_state) + parent_cost

class Priority(object):
    def __init__(self, priority, data):
        self.priority = priority
        self.data = data
        
    def __lt__(self, other):
        return self.priority < other.priority

class Agent:  # Do not change the name of this class!
    """
    An agent class, with DFS
    """
    def search_for_longest_route(self, board: GameBoard) -> List[Action]:
        """
        This algorithm search for an action sequence that makes the longest trading route at the end of the game.
        If there's no solution, then return an empty list.

        :param board: Game board to manipulate
        :return: List of actions
        """
        # Set up frontiers as FIFO Queue
        frontier = PriorityQueue()
        # Read initial state
        initial_state = board.get_initial_state()
        frontier.put(Priority(0, initial_state))
        reached = {initial_state['state_id']: 0}
        escaping_routes = 10

        # Until the frontier is nonempty,
        while not frontier.empty():
            # Read a state to search further
            state = frontier.get().data
            board.set_to_state(state)

            # If it is the game end, then read action sequences by back-tracing the actions.
            if board.is_game_end():
                return _make_action_sequence(state)
            
            # Build applicable actions
            possible_actions = []
            
            # 1) UPGRADE - 최장경로 10 이상이면 우선 탈출
            if len(board.get_applicable_cities()) > 1 or board.get_longest_route() >= escaping_routes:
                possible_actions += [(1, UPGRADE(v))
                                    for v in board.get_applicable_cities()]
                
            # 2) VILLAGE - 역시 10 이상일 시 탈출을 위함
            if board.get_longest_route() >= escaping_routes:
                possible_actions += [(1, VILLAGE(v))
                                    for v in board.get_applicable_villages()]
                
            # 2) ROAD
            possible_actions += [(2, ROAD(road))
                                 for road in board.get_applicable_roads()]
            
            # 3) PASS
            possible_actions += [(4, PASS())]
            
            # 4) TRADE - WOOD, BRICK으로의 교환만 생각할것임
            possible_actions += [(3, TRADE(r, r2))
                                  for r in RESOURCES
                                  if board.get_trading_rate(r) > 0
                                  for r2 in ['LUMBER', 'BRICK']
                                  if r != r2]

            # Expand next states
            for cost, action in possible_actions:
                child = board.simulate_action(state, action)
                pathCost = _pathCost(child) + cost

                # If the next state is already reached, then pass to the next action
                if child['state_id'] in reached and pathCost >= reached[child['state_id']]:
                    continue
                
                # Add parent information to the next state
                child['parent'] = (state, action, cost)
                frontier.put(Priority(pathCost, child))
                reached[child['state_id']] = pathCost

        # Return empty list if search fails.
        return []