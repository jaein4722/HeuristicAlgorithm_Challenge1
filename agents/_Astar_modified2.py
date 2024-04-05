from pathlib import Path
from typing import List

from action import *
from board import GameBoard, RESOURCES
from queue import LifoQueue, PriorityQueue, Queue

MAX_ROAD = 10

def _make_action_sequence(state: dict) -> List[Action]:
    # If there is no parent specified in the state, then it is an initial action.
    if 'parent' not in state:
        return []

    # Move back to the parent state, and read the action sequence until that state.
    parental_state, parent_action = state['parent']
    # Append the required action to reach the current state at the end of the parent's action list.
    return _make_action_sequence(parental_state) + [parent_action]

def Heuristic(board: GameBoard) -> int:
    if board.get_longest_route() >= MAX_ROAD - 1:
        return 0
    else:
        return MAX_ROAD - board.get_longest_route()
    
def real_distance(settle1: tuple, settle2: tuple):
    return abs(settle1[0] - settle2[0]) + abs(settle1[1] - settle2[1])
    
def detect_other(settle1: tuple, settle2: tuple, other_settles: dict, my_id: int):
    if settle1[0] < settle2[0]:
        settle1, settle2 = settle2, settle1
    gradient = (settle1[0] - settle2[0]) / (settle1[1] - settle2[1])
    while not (settle1[0] == min(settle2[0], settle2[1]) or settle1[1] == min(settle2[0], settle2[1])):
        # 두 settle을 이은 직선의 기울기에 따라 좌표 계산이 달라짐
        if gradient > 0 : 
            settle1 = (settle1[0] - 1, settle1[1] - 1)
            if settle1 in other_settles and other_settles[settle1]['owner'] != my_id:
                return MAX_ROAD - 1
        elif gradient < 0 :
            settle1 = (settle1[0] - 2, settle1[1] + 1)
            if settle1 in other_settles and other_settles[settle1]['owner'] != my_id:
                return MAX_ROAD - 1
        else:
            # 두 settle이 적당히 멀면서 한 수직선 상에 있음 -> 최대 길이 불가, 작게 설정
            return MAX_ROAD - 1
    return MAX_ROAD
    
def escape_Heuristic(board: GameBoard) -> int:
    '''
    최대로 이을 수 있는 도로의 수를 추정하는 휴리스틱 함수
    return: 최대로 이을 수 있는 도로 길이의 추정값 (9 or 10)
    '''
    state = board.get_state()
    my_id = state['player_id']
    
    if len(board.get_applicable_villages()) == 3:
        return MAX_ROAD
    elif len(board.get_applicable_villages()) == 4:
        settle1, settle2, settle3, settle4 = board.get_applicable_villages()
    
    distances = []
    other_settles = state['board']['intersections']

    if real_distance(settle1, settle2) == 1:
        distances.append(real_distance(settle1, settle3))
        distances.append(real_distance(settle1, settle4))
        distances.append(real_distance(settle2, settle3))
        distances.append(real_distance(settle2, settle4))
        if min(distances) >= 8:
            return MAX_ROAD-1
        elif min(distances) >= 6:
            if distances.index(min(distances)) == 0:
                return detect_other(settle1, settle3, other_settles, my_id)
            elif distances.index(min(distances)) == 1:
                return detect_other(settle1,settle4, other_settles, my_id)
            elif distances.index(min(distances)) == 2:
                return detect_other(settle2, settle3, other_settles, my_id)
            else:
                return detect_other(settle2, settle4, other_settles, my_id)
        else:
            return MAX_ROAD
    elif real_distance(settle1, settle3) == 1:
        distances.append(real_distance(settle1, settle2))
        distances.append(real_distance(settle1, settle4))
        distances.append(real_distance(settle3, settle2))
        distances.append(real_distance(settle3, settle4))
        if min(distances) >= 8:
            return MAX_ROAD-1
        elif min(distances) >= 6:
            if distances.index(min(distances)) == 0:
                return detect_other(settle1, settle2, other_settles, my_id)
            elif distances.index(min(distances)) == 1:
                return detect_other(settle1,settle4, other_settles, my_id)
            elif distances.index(min(distances)) == 2:
                return detect_other(settle3, settle2, other_settles, my_id)
            else:
                return detect_other(settle3, settle4, other_settles, my_id)
        else:
            return MAX_ROAD
    elif real_distance(settle1, settle4) == 1:
        distances.append(real_distance(settle1, settle2))
        distances.append(real_distance(settle1, settle3))
        distances.append(real_distance(settle4, settle2))
        distances.append(real_distance(settle4, settle3))
        if min(distances) >= 8:
            return MAX_ROAD-1
        elif min(distances) >= 6:
            if distances.index(min(distances)) == 0:
                return detect_other(settle1, settle2, other_settles, my_id)
            elif distances.index(min(distances)) == 1:
                return detect_other(settle1, settle3, other_settles, my_id)
            elif distances.index(min(distances)) == 2:
                return detect_other(settle4, settle2, other_settles, my_id)
            else:
                return detect_other(settle4, settle3, other_settles, my_id)
        else:
            return MAX_ROAD
    else:
        return MAX_ROAD
    


def topK(frontier: PriorityQueue, k: int) -> PriorityQueue:
    new_frontier = PriorityQueue()
    if frontier.qsize() <= k:
        return frontier
    for _ in range(k):
        new_frontier.put(frontier.get())
    return new_frontier

def find_ancestors(state: dict) -> list:
    if 'parent' not in state:
        return [state['state_id']]
    
    parental_state, parent_action = state['parent']
    return find_ancestors(parental_state) + [state['state_id']]

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
    
    def search_for_longest_route(self, board: GameBoard) -> List[Action]:
        """
        This algorithm search for an action sequence that makes the longest trading route at the end of the game.
        If there's no solution, then return an empty list.

        :param board: Game board to manipulate
        :return: List of actions
        """
        # Set up frontiers as Priority Queue
        frontier = PriorityQueue()
        # Read initial state
        initial_state = board.get_initial_state()
        
        initial_state['pathCost'] = 0
        initial_heuristic = Heuristic(board)
        
        board.set_to_state(initial_state)
        self.escaping_routes = escape_Heuristic(board)
        print(self.escaping_routes)
        
        frontier.put(Priority(initial_state['pathCost'] + initial_heuristic, initial_state))
        reached = {initial_state['state_id']: initial_state['pathCost'] + initial_heuristic}

        # Until the frontier is nonempty,
        while not frontier.empty():
            # Read a state to search further
            state = frontier.get().data
            board.set_to_state(state)
            precious_cost = state['pathCost']

            # If it is the game end, then read action sequences by back-tracing the actions.
            if board.is_game_end():
                return _make_action_sequence(state)
            
            # Build applicable actions
            possible_actions = self.make_possible_actions(board, self.escaping_routes)

            # Expand next states
            for cost, action in possible_actions:
                child = board.simulate_action(state, action)
                
                pathCost = precious_cost + cost
                h = Heuristic(board)
                fScore = pathCost + h

                # If the next state is already reached, then pass to the next action
                if child['state_id'] in reached and fScore >= reached[child['state_id']]:
                    continue
                
                # Add parent information to the next state
                child['parent'] = (state, action)
                child['pathCost'] = pathCost
                frontier.put(Priority(fScore, child))
                reached[child['state_id']] = fScore
            frontier = topK(frontier, 1000)

        # Return empty list if search fails.
        return []