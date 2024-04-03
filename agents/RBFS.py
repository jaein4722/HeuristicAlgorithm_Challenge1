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
            expanded.append(Priority(fCost, child))
            child['parent'] = (state, action)
            child['pathCost'] = pathCost

        if len(expanded) == 0:
            return [], INF
        
        for s in expanded:
            successors.put(Priority((), s.data))
        
        while True:
            best = expanded.get().data
            if best['pathCost'] > fLimit:
                return {}, best['pathCost']
            alternative = expanded.get().data
            result, best['pathCost'] = RBFS(board, best, min(fLimit, alternative['pathCost']), escaping_routes)

            if result != {}:
                return result, best['pathCost']
    
    def search_for_longest_route(self, board: GameBoard) -> List[Action]:
        """
        This algorithm search for an action sequence that makes the longest trading route at the end of the game.
        If there's no solution, then return an empty list.

        :param board: Game board to manipulate
        :return: List of actions
        """
        


        # # Set up frontiers as FIFO Queue
        # frontier = PriorityQueue()
        # Read initial state
        initial_state = board.get_initial_state()
        # frontier.put(Priority(0 + _Heuristic(board), initial_state))
        initial_state['pathCost'] = 0
        escaping_routes = 9
        RBFS(board, initial_state, float("inf"), escaping_routes)

        # # Until the frontier is nonempty,
        # while not frontier.empty():
        #     # Read a state to search further
        #     state = frontier.get().data
        #     board.set_to_state(state)

        #     # If it is the game end, then read action sequences by back-tracing the actions.
        #     if board.is_game_end():
        #         return _make_action_sequence(state)
            
        #     # Build applicable actions
        #     possible_actions = []
            
        #     # 1) UPGRADE - ������ 10 �̻��̸� �켱 Ż��, �� ó������ ������ village
        #     if len(board.get_applicable_cities()) > 1 or board.get_longest_route() >= escaping_routes:
        #         possible_actions += [(1, UPGRADE(v))
        #                             for v in board.get_applicable_cities()]
                
        #     # 2) VILLAGE - ���� 10 �̻��� �� Ż���� ����
        #     if board.get_longest_route() >= escaping_routes:
        #         possible_actions += [(1, VILLAGE(v))
        #                             for v in board.get_applicable_villages()]
                
        #     # 2) ROAD
        #     possible_actions += [(1, ROAD(road))
        #                          for road in board.get_applicable_roads()]
            
        #     # 3) PASS
        #     possible_actions += [(3, PASS())]
            
        #     # 4) TRADE - WOOD, BRICK������ ��ȯ�� �����Ұ���
        #     possible_actions += [(5, TRADE(r, r2))
        #                           for r in RESOURCES
        #                           if board.get_trading_rate(r) > 0
        #                           for r2 in ['Lumber', 'Brick']
        #                           if r != r2]

        #     # Expand next states
        #     for cost, action in possible_actions:
        #         child = board.simulate_action(state, action)
        #         pathCost = _pathCost(child) + cost
        #         h = _Heuristic(board)

        #         # If the next state is already reached, then pass to the next action
        #         if child['state_id'] in reached and pathCost + h >= reached[child['state_id']]:
        #             continue
                
        #         # Add parent information to the next state
        #         child['parent'] = (state, action, cost)
        #         frontier.put(Priority(pathCost + h, child))
        #         reached[child['state_id']] = pathCost + h
        # # Return empty list if search fails.
        # return []