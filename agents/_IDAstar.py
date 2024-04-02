from pathlib import Path
from typing import List

from action import *
from board import GameBoard, RESOURCES
from queue import LifoQueue, PriorityQueue, Queue

MAX_ROAD = 10
INF = 10000000

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

def _Heuristic(board: GameBoard) -> int:
    return MAX_ROAD - board.get_longest_route()

def topK(frontier: PriorityQueue, k: int) -> PriorityQueue:
    new_frontier = PriorityQueue()
    if frontier.qsize() <= k:
        return frontier
    for _ in range(k):
        new_frontier.put(frontier.get())
    return new_frontier

def find_ancestors(state: dict) -> list:
    if 'parent' not in state:
        return []
    
    parental_state, parent_action, parent_cost = state['parent']
    return find_ancestors(parental_state) + [parental_state['state_id']]

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
    def __init__(self):
        self.escaping_routes = 9
    
    def make_possible_actions(self, board: GameBoard, escaping_routes: int) -> list:
        possible_actions = []
        
        # 1) UPGRADE - 최장경로 10 이상이면 우선 탈출, or 가능하다면 UPGRADE 먼저 시행
        if len(board.get_applicable_cities()) > 1 or board.get_longest_route() >= escaping_routes:
            possible_actions += [(1, UPGRADE(v))
                                for v in board.get_applicable_cities()]
            
        # 2) VILLAGE - 역시 10 이상일 시 탈출을 위함
        if board.get_longest_route() >= escaping_routes:
            possible_actions += [(1, VILLAGE(v))
                                for v in board.get_applicable_villages()]
            
        # 3) ROAD
        possible_actions += [(1, ROAD(road))
                                for road in board.get_applicable_roads()]
        
        # 4) PASS
        possible_actions += [(3, PASS())]
        
        # 5) TRADE - WOOD, BRICK으로의 교환만 생각할것임
        possible_actions += [(5, TRADE(r, r2))
                                for r in ['Ore', 'Wool', 'Grain']
                                if board.get_trading_rate(r) > 0
                                for r2 in ['Lumber', 'Brick']
                                if r != r2]
        return possible_actions
    
    def CostLimitedA(self, board: GameBoard, state: dict, costLimit: int):
        board.set_to_state(state)
        fCost = _pathCost(state) + _Heuristic(board)
        if fCost > costLimit:
            return ('cut-off', fCost)
        if board.is_game_end():
            return (state, 0)
        
        nextLimit = INF
        possible_actions = self.make_possible_actions(board, self.escaping_routes)
        ancestors = find_ancestors(state)
        for cost, action in possible_actions:
            child = board.simulate_action(state, action)
            child['parent'] = (state, action, cost)
            
            if child['state_id'] not in ancestors:
                result, newLimit = self.CostLimitedA(board, child, costLimit)
                if result!= 'cut-off':
                    board.set_to_state(result)
                if board.is_game_end():
                    return (result, 0)
                if result != 'cut-off':
                    board.set_to_state(state)
                nextLimit = min(newLimit, nextLimit)
        return (result, nextLimit)
    
    def search_for_longest_route(self, board: GameBoard) -> List[Action]:
        """
        This algorithm search for an action sequence that makes the longest trading route at the end of the game.
        If there's no solution, then return an empty list.

        :param board: Game board to manipulate
        :return: List of actions
        """
        # Read initial state
        initial_state = board.get_initial_state()

        costLimit = _Heuristic(board)
        while costLimit < INF:
            print(costLimit)
            result, costLimit = self.CostLimitedA(board, initial_state, costLimit)
            if result != 'cut-off':
                return _make_action_sequence(result)
        return []