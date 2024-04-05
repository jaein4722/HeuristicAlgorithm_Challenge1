from pathlib import Path
from typing import List

from action import *
from board import GameBoard, RESOURCES
from queue import LifoQueue, PriorityQueue, Queue

import sys  
sys.setrecursionlimit(10000)

MAX_ROAD = 10
INF = 100000

def _make_action_sequence(state: dict) -> List[Action]:
    # If there is no parent specified in the state, then it is an initial action.
    if 'parent' not in state:
        return []

    # Move back to the parent state, and read the action sequence until that state.
    parental_state, parent_action = state['parent']
    # Append the required action to reach the current state at the end of the parent's action list.
    return _make_action_sequence(parental_state) + [parent_action]


def _Heuristic(board: GameBoard) -> int:
    return MAX_ROAD - board.get_longest_route()


def topK(frontier: PriorityQueue, k: int) -> PriorityQueue:
    new_frontier = PriorityQueue()
    if frontier.qsize() <= k:
        return frontier
    for _ in range(k):
        new_frontier.put(frontier.get())
    return new_frontier

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
        self.escaping_routes = 0
    
    def make_possible_actions(self, board: GameBoard) -> list:
        
        possible_actions = []
        
        # 1) UPGRADE - 최장경로 10 이상이면 우선 탈출, or 가능하다면 UPGRADE 먼저 시행
        if len(board.get_applicable_cities()) > 1 or board.get_longest_route() >= self.escaping_routes:
            possible_actions += [(1, UPGRADE(v))
                                for v in board.get_applicable_cities()]
            
        # 2) VILLAGE - 역시 10 이상일 시 탈출을 위함
        if board.get_longest_route() >= self.escaping_routes:
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
    
    def RBFS(self, board: GameBoard, state: dict, fLimit: float):
        board.set_to_state(state)
        if board.is_game_end():
            return _make_action_sequence(state), 0
        # Build applicable actions
        possible_actions = self.make_possible_actions(board)
        
        # Unlike normal RBFS, we use PriorityQueue instead of List
        # -> I think it is better to choose 'best'.
        expanded = [Priority]
        successors = PriorityQueue()

        #expand
        for cost, action in possible_actions:
            child = board.simulate_action(state, action)
            pathCost = state['pathCost'] + cost
            h = _Heuristic(board)
            fCost = pathCost+h
            child['parent'] = (state, action)
            child['pathCost'] = pathCost
            
            # set PathMax Heuristic
            child['fCost'] = max(fCost, state['fCost'])
            expanded.append(Priority(child['fCost'], child))

        if len(expanded) == 0:
            return [], INF
        
        for s in expanded:
            successors.put(s)
        
        while True:
            best = successors.get().data
            if best['fCost'] > fLimit:
                return [], best['fCost']
            alternative = successors.get().data
            result, best['fCost'] = self.RBFS(board, best, min(fLimit, alternative['fCost']))

            if result != []:
                return result, best['fCost']
    
    def search_for_longest_route(self, board: GameBoard) -> List[Action]:
        """
        This algorithm search for an action sequence that makes the longest trading route at the end of the game.
        If there's no solution, then return an empty list.

        :param board: Game board to manipulate
        :return: List of actions
        """
        initial_state = board.get_initial_state()
        board.set_to_state(initial_state)
        
        initial_state['pathCost'] = 0
        initial_state['fCost'] = initial_state['pathCost'] + _Heuristic(board)
        escaping_routes = 10
        
        return self.RBFS(board, initial_state, float("inf"), escaping_routes)