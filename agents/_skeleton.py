from pathlib import Path
from typing import List

from action import Action
from board import GameBoard
from queue import Queue


class Agent:  # Do not change the name of this class!
    """
    An agent class
    """
    def search_for_longest_route(self, board: GameBoard) -> List[Action]:
        """
        This algorithm search for an action sequence that makes the longest trading route at the end of the game.
        If there's no solution, then return an empty list.

        :param board: Game board to manipulate
        :return: List of actions
        """

        raise NotImplementedError()
        # Remove the above code and write a code that returns list of actions.