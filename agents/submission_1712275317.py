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
    
def real_distance(s1: tuple, s2: tuple):
    if s2[0] > s1[0]:
        return s2[1] - s1[1] + s2[0] - s1[0]
    elif s1[0] + s1[1] > s2[0] +s2[1]:
        return s1[0] - s2[0]
    else:
        return s2[1] - s1[1]
    
def escape_Heuristic(board: GameBoard) -> int:
    '''
    ìµëë¡ ì´ì ì ìë ëë¡ì ìë¥¼ ì¶ì íë í´ë¦¬ì¤í± í¨ì
    return: ìµëë¡ ì´ì ì ìë ëë¡ ê¸¸ì´ì ì¶ì ê° (9 or 10)
    '''
    state = board.get_state()
    my_id = state['player_id']
    assert len(board.get_applicable_cities()) == 2
    settle1, settle2 = board.get_applicable_cities()
    
    if settle1[1] > settle2[1]:
        settle1, settle2 = settle2, settle1
    # ì¶ì  ê±°ë¦¬ ê³ì° - ë settleì ê° ì¢íì ì°¨ì´ë¥¼ ëí´ ì¶ì  ê±°ë¦¬ë¥¼ êµ¬í´ë³¸ë¤
    estimated_distance = real_distance(settle1, settle2)
    other_settles = state['board']['intersections']
    
    if estimated_distance >= 10:
        # ì¶ì  ê±°ë¦¬ê° 10ë³´ë¤ ë©ë©´, ì§ì  ê·¸ë ¤ë´¤ì ë ìµë ëë¡ ê¸¸ì´ì¸ 10ê°ë¥¼ ê¹ ìê° ìì
        # ë°ë¼ì íë ì ê² íì¶ê°ì ì¤ì 
        return MAX_ROAD - 1
    elif estimated_distance >= 8:
        # ë settle ì¬ì´ê° ëë¬´ ë©ì§ ìê³  ì ë¹í ë© ë,
        # ëì ë settle ì¬ì´ë¥¼ ëê°ì ì¼ë¡ ê·¸ì´, ê·¸ ìì ë¤ë¥¸ íë ì´ì´ì settleì´ ìëì§ íë³
        # ìë¤ë©´ ìµë ê¸¸ì´ë³´ë¤ ìê², ìë¤ë©´ ìµë ê¸¸ì´ë¡ ì¤ì 
        gradient = (settle1[0] - settle2[0]) / (settle1[1] - settle2[1])
        while not (settle1[0] == min(settle2[0], settle2[1]) or settle1[1] == min(settle2[0], settle2[1])):
            # ë settleì ì´ì ì§ì ì ê¸°ì¸ê¸°ì ë°ë¼ ì¢í ê³ì°ì´ ë¬ë¼ì§
            if gradient > 0 : 
                settle1 = (settle1[0] - 1, settle1[1] - 1)
                if settle1 in other_settles and other_settles[settle1]['owner'] != my_id:
                    return MAX_ROAD - 1
            elif gradient < 0 :
                settle1 = (settle1[0] - 2, settle1[1] + 1)
                if settle1 in other_settles and other_settles[settle1]['owner'] != my_id:
                    return MAX_ROAD - 1
            else:
                # ë settleì´ ì ë¹í ë©ë©´ì í ìì§ì  ìì ìì -> ìµë ê¸¸ì´ ë¶ê°, ìê² ì¤ì 
                return MAX_ROAD - 1
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
        
        # 1) UPGRADE - ìµì¥ê²½ë¡ 10 ì´ìì´ë©´ ì°ì  íì¶, or ê°ë¥íë¤ë©´ UPGRADE ë¨¼ì  ìí
        if len(board.get_applicable_cities()) > 1 or board.get_longest_route() >= escaping_routes:
            possible_actions += [(0, UPGRADE(v))
                                for v in board.get_applicable_cities()]
            
        # 2) VILLAGE - ì­ì 10 ì´ìì¼ ì íì¶ì ìí¨
        if board.get_longest_route() >= escaping_routes:
            possible_actions += [(1, VILLAGE(v))
                                for v in board.get_applicable_villages()]
            
        # 3) ROAD
        possible_actions += [(2, ROAD(road))
                                for road in board.get_applicable_roads()]
        
        # 4) PASS
        possible_actions += [(5, PASS())]
        
        # # 5) TRADE - WOOD, BRICKì¼ë¡ì êµíë§ ìê°í ê²ì
        # possible_actions += [(5, TRADE(r, r2))
        #                         for r in ['Ore', 'Wool', 'Grain']
        #                         if board.get_trading_rate(r) > 0
        #                         for r2 in ['Lumber', 'Brick']
        #                         if r != r2]
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