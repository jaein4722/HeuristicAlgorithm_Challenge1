# Logging method for board execution
import logging
# Library for OS environment
import os
import sys
# Object-level deep copy method
from copy import deepcopy
# Random number generators
from random import randint as random_integer, choice as random_choice, shuffle as random_shuffle
# Type specification for Python code
from typing import Tuple, List, Dict

# Import some class definitions that implements the Settlers of Catan game.
from pycatan import Game, Resource
from pycatan.board import RandomBoard, BuildingType, Building, BoardRenderer

# Process information class: for memory usage tracking
from psutil import Process as PUInfo, NoSuchProcess

# Import action specifications
from action import Action
# Import some utilities
from util import tuple_to_coordinate, count_building, coordinate_to_tuple, tuple_to_path_coordinate


#: True if the program run with 'DEBUG' environment variable.
IS_DEBUG = '--debug' in sys.argv
# Initialize logger
logging.basicConfig(level=logging.DEBUG if IS_DEBUG else logging.INFO,
                    format='%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s',
                    filename=f'execution-{os.getpid()}.log',
                    # Also, the output will be logged in 'execution-(pid).log' file.
                    filemode='w+')  # The logging file will be overwritten.


# String List of available resources
RESOURCES = [
    Resource.ORE.name,
    Resource.WOOL.name,
    Resource.BRICK.name,
    Resource.GRAIN.name,
    Resource.LUMBER.name
]


def _coordinate_to_identifier(c):
    """
    Return the unique identifier for a coordinate on the board.
    :param c: Coordinate to make an identifier
    :return: 2-character String identifier for Coordinate c
    """
    q, r = coordinate_to_tuple(c)
    q = chr(ord('L') + int(q))
    r = chr(ord('L') + int(r))
    return q + r


def _unique_game_state_identifier(game: Game) -> str:
    """
    Return the unique identifier for game states.
    If two states are having the same identifier, then the states can be treated as identical in this problem.

    :param game: Game to make a unique identifier
    :return: String of game identifier
    """

    hexes = ':'.join([
        _coordinate_to_identifier(c) + str(h.hex_type.value)
        for c, h in sorted(game.board.hexes.items(), key=lambda t: t[1].token_number or -1)
    ])
    intersections = ':'.join([
        _coordinate_to_identifier(c) + str(game.players.index(i.building.owner)) + str(i.building.building_type.value)
        for c, i in game.board.intersections.items()
        if i.building is not None
    ])
    paths = ':'.join([
        '-'.join(sorted(_coordinate_to_identifier(c) for c in p)) + str(game.players.index(i.building.owner))
        for p, i in game.board.paths.items()
        if i.building is not None
    ])
    players = ':'.join([
        '.'.join(str(r.value) + str(c) for r, c in sorted(p.resources.items(), key=lambda t: t[0].name))
        for p in game.players
    ])
    harbors = ':'.join([
        '-'.join(sorted(_coordinate_to_identifier(c) for c in p)) +
        (str(i.resource.value) if i.resource is not None else 'X')
        for p, i in game.board.harbors.items()
    ])

    return f'{hexes}/{intersections}/{paths}/{players}/{harbors}'


def _read_state(game: Game, player: int) -> dict:
    """
    Helper function for reading the current state representation as a python dictionary from the PyCatan board.

    :param game: Game to build a state.
    :return: State representation of a game (in basic python objects)
    """

    return {
        'state_id': _unique_game_state_identifier(game),
        # Unique identifier for the game state. If this is the same, then the state will be equivalent.
        'player_id': player, # Player ID
        'board': {  # Information about the current board
            'hexes': {  # Information about each hexagon cell
                coordinate_to_tuple(c): {  # For each coordinate(placement)
                    'type': h.hex_type.name,  # Resource type of that hexagon
                    'dice': h.token_number  # Dice number for that hexagon
                }
                for c, h in game.board.hexes.items()
            },
            'intersections': {  # Information about node intersection among three hexagon cells
                coordinate_to_tuple(c): {  # For each coordinate (placement)
                    'type': i.building.building_type.name if i.building is not None else None,  # Type of building
                    'owner': game.players.index(i.building.owner) if i.building is not None else None
                    # Owner of building
                }
                for c, i in game.board.intersections.items()
            },
            'paths': {  # Information about edge intersection between two hexagon cells
                tuple(sorted(coordinate_to_tuple(c) for c in p)): {  # For each edge (placement)
                    'type': i.building is not None,  # Road constructed or not (boolean)
                    'owner': game.players.index(i.building.owner) if i.building is not None else None  # Owner of path
                }
                for p, i in game.board.paths.items()
            },
            'harbors': {  # Information about harbors
                tuple(sorted(coordinate_to_tuple(c) for c in p)): {  # For each coordinate of harbor,
                    'type': i.resource.name if i.resource is not None else None
                    # Resource type for that harbor(2:1 trade). None means generic harbor(3:1)
                }
                for p, i in game.board.harbors.items()
            },
        },
        'player': {  # Information about the current player
            'resources': {  # Information about resource cards
                res.name: cnt  # For each resource, the number of resource cards will be stored
                for res, cnt in game.players[player].resources.items()
            },
            'harbors': [  # Information about the connected harbors, with the coordinate names
                tuple(sorted(coordinate_to_tuple(c) for c in h.path_coords))
                for h in game.players[player].connected_harbors
            ]
        }
    }


def _restore_state(game: Game, state: dict):
    """
    Helper function to restore board state to given state representation.

    :param game: Game to restore a state.
    :param state: State to be restored
    """
    # Read player id
    player = state['player_id']

    # Check whether hexes are the same.
    for c, h in state['board']['hexes'].items():
        c = tuple_to_coordinate(c)
        assert game.board.hexes[c].hex_type.name == h['type'], 'The hex information (hex type) is different!'
        assert game.board.hexes[c].token_number == h['dice'], 'The hex information (hex token) is different!'

    # Check whether harbors are the same.
    for (c1, c2), i in state['board']['harbors'].items():
        c = tuple_to_path_coordinate((c1, c2))
        res = game.board.harbors[c].resource

        assert (res is None and i['type'] is None) or (res.name == i['type']), 'Harbor information is different!'

    # Restore intersections
    for c, i in state['board']['intersections'].items():
        c = tuple_to_coordinate(c)
        building = None
        if i['type'] is not None:
            building = Building(building_type=BuildingType[i['type']], owner=game.players[i['owner']])

        game.board.intersections[c].building = building

    # Restore paths
    for (c1, c2), i in state['board']['paths'].items():
        c = tuple_to_path_coordinate((c1, c2))
        building = None
        if i['type']:
            building = Building(building_type=BuildingType.ROAD, owner=game.players[i['owner']])

        game.board.paths[c].building = building

    # Restore player's resource
    for res, cnt in state['player']['resources'].items():
        res = Resource[res.upper()]
        game.players[player].resources[res] = cnt

    # Restore connected harbor information
    game.players[player].connected_harbors = set()
    for (c1, c2) in state['player']['harbors']:
        c = tuple_to_path_coordinate((c1, c2))
        game.players[player].connected_harbors.add(game.board.harbors[c])

    return player


class GameBoard:
    """
    The game board object.
    By interacting with Board, you can expect what will happen afterward.
    """
    #: [PRIVATE] The game instance running currently. Don't access this directly in your agent code!
    _game = None
    #: [PRIVATE] The game renderer
    _renderer = None
    #: [PRIVATE] The order of your turn. Don't access this directly in your agent code!
    _player_number = 0
    #: [PRIVATE] The initial state of the board. Don't access this directly in your agent code!
    _initial = None
    #: [PRIVATE] The current state of the board. Don't access this directly in your agent code!
    _current = None
    #: [PRIVATE] The order of dice roll. Don't access this directly in your agent code!
    _dice_roll_order = []
    #: [PRIVATE] The number of current turn. Don't access this directly in your agent code!
    _dice_roll = 0
    #: [PRIVATE] Logger instance for Board's function calls
    _logger = logging.getLogger('GameBoard')
    #: [PRIVATE] Memory usage tracker
    _process_info = None
    #: [PRIVATE] Maximum memory usage. Don't access this directly in your agent code!
    _max_memory = 0

    def _initialize(self):
        """
        Initialize the board for evaluation. ONLY for evaluation purposes.
        [WARN] Don't access this method in your agent code.
        """
        # Initialize process tracker
        self._process_info = PUInfo(os.getpid())

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('Initializing a new game board...')
        # Initialize a new game board
        self._game = Game(RandomBoard())
        # Initialize board renderer for debugging purposes
        if IS_DEBUG:  # Logging for debug
            self._renderer = BoardRenderer(self._game.board)
            self._logger.debug('Rendered board: \n' + _unique_game_state_identifier(self._game))
            self._renderer.render_board()

        # Take a player as you
        self._player_number = random_integer(0, 3)
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'You\'re player {self._player_number}')

        # Set an order for dice roll (not used actually)
        self._dice_roll_order = [i + j for i in range(1, 7) for j in range(1, 7)]
        self._dice_roll = 0
        random_shuffle(self._dice_roll_order)
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'The order of dice rolls = {self._dice_roll_order}')

        # Place a random village and a road for each player
        for idx in list(range(4)) + list(reversed(range(4))):  # For each player, in the order of 1-2-3-4-4-3-2-1.
            player = self._game.players[idx]

            # Query all applicable nodes for the initial village.
            applicable_nodes = self._game.board.get_valid_settlement_coords(player, ensure_connected=False)
            # Choose a random node
            chosen_node = random_choice(list(applicable_nodes))
            # Make the initial village(settlement)
            self._game.build_settlement(player=player, coords=chosen_node,
                                        cost_resources=False, ensure_connected=False)

            # Query all applicable road options adjacent to the lastly built village
            applicable_edges = self._game.board.get_valid_road_coords(player, connected_intersection=chosen_node)
            # Choose a random edge
            chosen_path = random_choice(list(applicable_edges))
            # Make the initial route
            self._game.build_road(player=player, path_coords=chosen_path, cost_resources=False)

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('After constructing initial village: \n' + _unique_game_state_identifier(self._game))
            self._renderer.render_board()

        # Run until the current dice roll matches with the player ID (pass the other players)
        for _ in range(self._player_number + 1):
            # For each player, roll the dice (deterministically)
            next_dice = self.get_next_dice_roll()

            # If the dice number is 7, do nothing.
            if next_dice == 7:
                pass
            else:
                # Otherwise, give resources to the players
                self._add_yield()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('Current resources: \n' + str(self._game.players[self._player_number].resources))
            self._logger.debug(f'The current turn number is now {self._dice_roll}')

        # Store initial state representation
        self._initial = _read_state(self._game, self._player_number)
        self._initial['dice_roll'] = self._dice_roll

        self._current = deepcopy(self._initial)

        # Update memory usage
        self._update_memory_usage()

    def _add_yield(self):
        """
        Add yield for every turn, as specified in the README.md file.
        """

        # Query the player's current building state
        player = self._game.players[self._player_number]
        bldg_count = count_building(self._game.board.intersections.values(), player)
        multiple = 1 + bldg_count[BuildingType.CITY]

        player.add_resources({
            Resource[r.upper()]: multiple
            for r in RESOURCES
        })

    def set_to_state(self, specific_state=None):
        """
        Restore the board to the initial state for repeated evaluation.

        :param specific_state: A state representation which the board reset to
        """
        if specific_state is None:
            specific_state = self._initial

        # Restore the board to the given state.
        self._player_number = _restore_state(self._game, specific_state)
        self._dice_roll = specific_state['dice_roll']

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('State has been set as follows: \n' + _unique_game_state_identifier(self._game))
            self._logger.debug(f'The current turn number is now {self._dice_roll}')
            self._renderer.render_board()

    def is_game_end(self):
        """
        Check whether the given state indicate the end of the game

        :param state: A state to check. If None, then it will use the initial state.
        :return: True if the game ends at the given state
        """
        is_game_end = self._game.get_victory_points(self._game.players[self._player_number]) >= 4
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Querying whether the game ends in this state... Answer = {is_game_end}')
        return is_game_end

    def get_initial_state(self) -> dict:
        """
        Get the initial board state

        :return: A copy of the initial board state dictionary
        """
        if IS_DEBUG:  # Logging for debug
            self._logger.debug('Querying initial state...')

        # Check whether the game has been initialized or not.
        assert self._initial is not None, 'The board should be initialized. Did you run the evaluation code properly?'
        # Return the initial state representation as a copy.
        return deepcopy(self._initial)

    def get_applicable_roads(self) -> List[Tuple[Tuple[int, int]]]:
        """
        Get the list of applicable roads

        :return: A copy of the list of applicable road coordinates.
            (List of Tuple[pair] of Coordinate tuples[Q, R].)
        """
        if IS_DEBUG:  # Logging for debug
            self._logger.debug('Querying applicable roads...')

        # Query the player's current building state
        player = self._game.players[self._player_number]
        path_count = count_building(self._game.board.paths.values(), player)

        # If the number of current road is 10, then we cannot build a road anymore.
        if path_count[BuildingType.ROAD] >= 10:
            if IS_DEBUG:  # Logging for debug
                self._logger.debug('All road blocks are already in use. You cannot construct it now.')
            return []

        # Read all applicable positions
        applicable_positions = \
            self._game.board.get_valid_road_coords(self._game.players[self._player_number],
                                                   ensure_connected=True)
        # Make it to a basic python tuples
        applicable_positions = [
            tuple(sorted([coordinate_to_tuple(coord) for coord in coord_set]))
            for coord_set in applicable_positions
        ]

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'List of applicable positions for a ROAD: {applicable_positions}')
        # Return applicable positions as list of tuples.
        return applicable_positions

    def get_applicable_villages(self) -> List[Tuple[int, int]]:
        """
        Get the list of applicable villages

        :return: A copy of the list of applicable village coordinates.
            (List of Coordinate tuples[Q, R].)
        """
        # Query the player's current building state
        player = self._game.players[self._player_number]
        village_count = count_building(self._game.board.intersections.values(), player)

        # If the number of current village is 3, then we cannot build a village anymore.
        if village_count[BuildingType.SETTLEMENT] >= 3:
            if IS_DEBUG:  # Logging for debug
                self._logger.debug('All village blocks are already in use. You cannot construct it now.')
            return []

        # Read all applicable positions
        applicable_positions = \
            self._game.board.get_valid_settlement_coords(player, ensure_connected=True)
        # Make it to a basic python tuples
        applicable_positions = [
            coordinate_to_tuple(coord)
            for coord in applicable_positions
        ]

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'List of applicable positions for a VILLAGE: {applicable_positions}')
        # Return applicable positions as list of tuples.
        return applicable_positions

    def get_applicable_cities(self) -> List[Tuple[int, int]]:
        """
        Get the list of applicable villages

        :return: A copy of the list of applicable village coordinates.
            (List of Coordinate tuples[Q, R].)
        """
        # Query the player's current building state
        player = self._game.players[self._player_number]
        village_count = count_building(self._game.board.intersections.values(), player)

        # If the number of current city is 3, then we cannot build a city anymore.
        if village_count[BuildingType.CITY] >= 3:
            if IS_DEBUG:  # Logging for debug
                self._logger.debug('All city blocks are already in use. You cannot construct it now.')
            return []

        # Read all applicable positions
        applicable_positions = \
            self._game.board.get_valid_city_coords(player)
        # Make it to a basic python tuples
        applicable_positions = [
            coordinate_to_tuple(coord)
            for coord in applicable_positions
        ]

        # Update memory usage
        self._update_memory_usage()

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'List of applicable positions for a CITY: {applicable_positions}')
        # Return applicable positions as list of tuples.
        return applicable_positions

    def get_resource_cards(self) -> Dict[str, int]:
        """
        Get the number of resource cards that the player have.

        :return: Dictionary of resource to number of cards mapping.
        """
        resources = {
            str(res): count
            for res, count in self._game.players[self._player_number].resources.items()
        }

        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Querying current resource counts: {resources}')

        # Update memory usage
        self._update_memory_usage()

        return resources

    def get_longest_route(self) -> int:
        """
        :return: The length of the longest trading route for the player.
        """
        long_route = self._game.board.calculate_player_longest_road(self._game.players[self._player_number])
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Querying the length of the longest route: {long_route}')

        # Update memory usage
        self._update_memory_usage()

        return long_route

    def get_trading_rate(self, resource: str) -> int:
        """
        Compute the trading rate for the given resources
        :param resource: The resource to sell
        :return: The minimum number of resources required to get one required resource.
        If trading is impossible, then -1 will be given.
        """
        # Get all possible trade conditions
        trading_conds = self._game.players[self._player_number].get_possible_trades()
        # Filter out other resources
        resource = Resource[resource.upper()]
        trading_conds = [-c[resource] for c in trading_conds
                         if c.get(resource, 0) < 0]

        if not trading_conds:
            # If you cannot do trading due to lack of resources, the trading rate will be returned as -1.
            if IS_DEBUG:  # Logging for debug
                self._logger.debug(f'Not enough {resource} resources for TRADE.')
            return -1

        # Return minimum trading rate
        min_cond = min(trading_conds)
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'To get one of other resource cards, you need {min_cond} {resource} cards.')

        # Update memory usage
        self._update_memory_usage()

        return min_cond

    def get_next_dice_roll(self) -> int:
        """
        Move to the next turn, and rolling dices.
        :return: The number from two dices.
        """

        # Move to the next turn
        self._dice_roll += 1
        # Get the dice number
        roll = self._dice_roll_order[self._dice_roll % len(self._dice_roll_order)]
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'Turn #{roll}: Dices give you the number {roll}.')

        # Update memory usage
        self._update_memory_usage()

        # Return it.
        return roll

    def get_current_memory_usage(self):
        """
        :return: Current memory usage for the process having this board
        """
        try:
            return self._process_info.memory_info().rss
        except NoSuchProcess:
            if self._max_memory >= 0:
                self._logger.warning('As tracking the process has been failed, '
                                     'I turned off memory usage tracking ability.')
                self._max_memory = -1
            return -1

    def get_max_memory_usage(self):
        """
        :return: Maximum memory usage for the process having this board
        """
        return self._max_memory

    def _update_memory_usage(self):
        """
        [PRIVATE] updating maximum memory usage
        """
        if self._max_memory >= 0:
            self._max_memory = max(self._max_memory, self.get_current_memory_usage())

    def simulate_action(self, state: dict = None, *actions: Action) -> dict:
        """
        Simulate given actions.

        Usage:
            - `simulate_action(state, action1)` will execute a single action, `action1`
            - `simulate_action(state, action1, action2)` will execute two consecutive actions, `action1` and `action2`
            - ...
            - `simulate_action(state, *action_list)` will execute actions in the order specified in the `action_list`

        :param state: State where the simulation starts from. If None, the simulation starts from the initial state.
        :param actions: Actions to simulate or execute.
        :return: The last state after simulating all actions
        """
        if IS_DEBUG:  # Logging for debug
            self._logger.debug(f'------- SIMULATION START: {actions} -------')

        # Restore to the given state
        self.set_to_state(state)

        for act in actions:  # For each actions in the variable arguments,
            # Run actions through calling each action object
            act(self)

            # Break the loop if the game ends within executing actions.
            if self.is_game_end():
                break

        # Copy the current state to return
        self._current = _read_state(self._game, self._player_number)
        self._current['dice_roll'] = self._dice_roll

        if IS_DEBUG:  # Logging for debug
            self._logger.debug('State has been changed to: \n' + _unique_game_state_identifier(self._game))
            self._logger.debug(f'The current turn number is now {self._dice_roll}')
            self._renderer.render_board()
            self._logger.debug('------- SIMULATION ENDS -------')

        # Update memory usage
        self._update_memory_usage()

        return deepcopy(self._current)


# Export only GameBoard and RESOURCES.
__all__ = ['GameBoard', 'RESOURCES', 'IS_DEBUG']
