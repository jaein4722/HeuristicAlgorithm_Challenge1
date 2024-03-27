# Package for logging your execution
import logging
import os
# Package for random seed control
import random
# A dictionary class which can set the default value
from collections import defaultdict
# Package for runtime importing
from importlib import import_module
# Package for multiprocessing (evaluation will be done with multiprocessing)
from multiprocessing import Process, Queue
# Querying function for the number of CPUs
from os import cpu_count
# Package for file handling
from pathlib import Path
from time import time, sleep
# Package for writing exceptions
from traceback import format_exc

# Memory usage tracking function
import psutil as pu

# Package for problem definitions
from board import *
# Function for loading your agents
from agents.load import get_all_agents

#: Size of MB in bytes
MEGABYTES = 1024 ** 2
#: The number of games to run the evaluation
GAMES = 5
#: LIMIT FOR A SINGLE EXECUTION, 60 minutes
TIME_LIMIT = 1000 * 60 * 60
#: LIMIT OF MEMORY USAGE, 4GB
MEMORY_LIMIT = 4 * 1024 * MEGABYTES

# Set a random seed
random.seed(5606)


def evaluate_algorithm(agent_name, initial_state, result_queue: Queue):
    """
    Run the evaluation for an agent.
    :param agent_name: Agent to be evaluated
    :param initial_state: Initial state for the test
    :param result_queue: A multiprocessing Queue to return the execution result.
    """
    # Set up the given problem
    problem = GameBoard()
    problem._initialize()
    problem.set_to_state(initial_state)

    # Log initial memory size
    init_memory = problem.get_current_memory_usage()
    logger = logging.getLogger('Evaluate')

    # Initialize an agent
    try:
        logger.info(f'Loading {agent_name} agent to memory...')
        module = import_module(f'agents.{agent_name}')
        agent = module.Agent()
    except Exception as e:
        # When agent loading fails, send the failure log to main process.
        failure = format_exc()
        logger.error('Loading failed!', exc_info=e)
        result_queue.put((agent_name, failure, 200, 0, float('inf')))
        return

    # Do search
    solution = None
    failure = None  # Record for Performance measure I
    longest_route = 0  # Record for Performance measure III
    num_actions = float('inf')  # Record for Performance measure IV

    logger.info(f'Begin to search using {agent_name} agent.')
    try:
        solution = agent.search_for_longest_route(problem)
        assert type(solution) is list, 'Solution should be a list!'
    except:
        failure = format_exc()

    # Get maximum memory usage during search (Performance measure II)
    max_memory_usage = int(max(0, problem.get_max_memory_usage() - init_memory) / MEGABYTES / 10) * 10
    logger.info(f'Search finished for {agent_name}, using {max_memory_usage}MB during search.')
    # Ignore memory usage below 200MB.
    max_memory_usage = max(200, max_memory_usage)

    # Execute the solution for evaluation
    if solution is not None:
        try:
            problem.simulate_action(initial_state, *solution)
            longest_route = problem.get_longest_route()  # Performance measure III
            num_actions = len(solution)  # Performance measure IV
            is_end = problem.is_game_end()  # Check whether this is the game's end.

            if not is_end:
                if failure:
                    failure = failure + '; '
                else:
                    failure = ''
                failure += 'The solution does not reach a goal state!'
        except:
            failure = format_exc()

    if IS_DEBUG:
        logger.debug(f'Execution Result: Failure {not not failure}, {max_memory_usage}MB, '
                     f'route with {longest_route} blocks, {num_actions} actions.')
    result_queue.put((agent_name, failure, max_memory_usage, longest_route, num_actions))


# Main function
if __name__ == '__main__':
    # Problem generator for the same execution
    prob_generator = GameBoard()
    # List of all agents
    all_agents = get_all_agents()

    # Performance measures
    failures = defaultdict(list)  # This will be counted across different games
    memory_ranksum = defaultdict(list)  # This will be computed as sum of rank across different games
    route_ranksum = defaultdict(list)  # This will be computed as sum of rank across different games
    act_ranksum = defaultdict(list)  # This will be computed as sum of rank across different games
    last_execution = defaultdict(lambda: (200, 0, float('inf')))

    def _compute_rank(sort, reverse=False):
        """
        Compute ranking

        :param sort: List of (key, value)
        :return: List of (key, ranks)
        """
        rank_key = None
        rank = []
        for i, (agent, _rank_key_i) in enumerate(sorted(sort, key=lambda t: t[1], reverse=reverse)):
            # Manage ties
            if rank_key != _rank_key_i:
                rank.append((agent, i + 1))
                rank_key = _rank_key_i
            else:
                rank.append((agent, rank[-1][1]))

        return rank


    def _print(t):
        """
        Helper function for printing rank table
        :param t: Game trial number
        """

        # Print header
        print(f'\nCurrent game trial: #{t}')
        print(f' StudentID    | #Failure  MemNow [RankSum]  RouteNow [RankSum]  Action [RankSum] |'
              f' Rank  Percentile')
        print('=' * 14 + '|' + '=' * 66 + '|' + '=' * 17)

        # Sort agents by performance measures
        for_ranking = [(k, (len(failures[k]),  # Failure in ascending order
                            sum(memory_ranksum[k]),  # Memory usage (rank sum) in ascending order
                            sum(route_ranksum[k]),  # Longest route (rank sum) in ascending order
                            sum(act_ranksum[k])))  # Number of actions (rank sum) in ascending order
                       for k in all_agents]

        for agent, rank in _compute_rank(for_ranking):
            # Name print option
            key_print = agent if len(agent) < 13 else agent[:9] + '...'
            # Compute percentile
            percentile = int(rank / len(for_ranking) * 100)
            # Print a row
            print(f' {key_print:12s} | {len(failures[agent]):8d} '
                  f' {last_execution[agent][0]:4d}MB [{sum(memory_ranksum[agent]):7d}] '
                  f' L= {last_execution[agent][1]:5d} [{sum(route_ranksum[agent]):7d}] '
                  f' {last_execution[agent][2]:6.0f} [{sum(act_ranksum[agent]):7d}] |'
                  f' {rank:4d}  {percentile:3d}th/100')

            # Write-down the failures
            with Path(f'./failure_{agent}.txt').open('w+t') as fp:
                fp.write('\n\n'.join(failures[agent]))

    # Start evaluation process (using multi-processing)
    process_results = Queue(len(all_agents) * 2)
    process_count = max(cpu_count() - 2, 1)

    def _execute(prob, agent_i):
        """
        Execute an evaluation for an agent with given initial state.
        :param prob: Initial state for a problem
        :param agent_i: Agent
        :return: A process
        """
        proc = Process(name=f'EvalProc', target=evaluate_algorithm, args=(agent_i, prob, process_results), daemon=True)
        proc.start()
        proc.agent = agent_i  # Make an agent tag for this process
        return proc


    def _read_result(res_queue, exceeds):
        """
        Read evaluation result from the queue.
        :param res_queue: Queue to read
        :param exceeds: failure message for agents who exceeded limits
        """
        while not res_queue.empty():
            agent_i, failure_i, mem_i, route_i, act_i = res_queue.get()
            if failure_i is None and not (agent_i in exceeds):
                last_execution[agent_i] = mem_i, route_i, act_i
            else:
                last_execution[agent_i] = 200, 0, float('inf')
                failures[agent_i].append(failure_i if failure_i else exceeds[agent_i])


    for trial in range(GAMES):
        # Clear all previous results
        last_execution.clear()
        while not process_results.empty():
            process_results.get()

        # Generate new problem
        prob_spec = prob_generator._initialize()
        logging.info(f'Trial {trial} begins!')

        # Execute agents
        processes = []
        agents_to_run = all_agents.copy()
        random.shuffle(agents_to_run)

        exceed_limit = {}  # Timeout limit
        while agents_to_run or processes:
            # If there is a room for new execution, execute new thing.
            if agents_to_run and len(processes) < process_count:
                alg = agents_to_run.pop()
                processes.append((_execute(prob_spec, alg), time()))

            new_proc_list = []
            for p, begin in processes:
                if not p.is_alive():
                    continue
                # For each running process, check for timeout
                if begin + TIME_LIMIT < time():
                    p.terminate()
                    exceed_limit[p.agent] = \
                        f'Process is running more than {TIME_LIMIT} sec, from ts={begin}; now={time()}'
                    logging.info(f'[TIMEOUT] {p.agent} / '
                                 f'Process is running more than {TIME_LIMIT} sec, from ts={begin}; now={time()}')
                else:
                    try:
                        p_bytes = pu.Process(p.pid).memory_info().rss
                        if p_bytes > MEMORY_LIMIT:
                            p.terminate()
                            exceed_limit[p.agent] = \
                                f'Process consumed memory more than {MEMORY_LIMIT / MEGABYTES}MB (used: {p_bytes / MEGABYTES}MB)'
                            logging.info(f'[MEM LIMIT] {p.agent} / '
                                         f'Process consumed memory more than {MEMORY_LIMIT / MEGABYTES}MB (used: {p_bytes / MEGABYTES}MB)')
                        else:
                            new_proc_list.append((p, begin))
                    except pu.NoSuchProcess:
                        new_proc_list.append((p, begin))

            # Prepare for the next round
            processes = new_proc_list
            # Read result from queue
            _read_result(process_results, exceed_limit)

            if len(processes) >= process_count:
                # Wait for one seconds
                sleep(1)

        # Read results
        logging.info(f'Reading results at Trial {trial}')
        _read_result(process_results, exceed_limit)

        # Sort the results for each performance criteria and give ranks to agents
        mem_ranks = dict(_compute_rank([(k, last_execution[k][0]) for k in all_agents]))
        rou_ranks = dict(_compute_rank([(k, last_execution[k][1]) for k in all_agents], reverse=True))
        act_ranks = dict(_compute_rank([(k, last_execution[k][2]) for k in all_agents]))

        # Store rankings
        for key in all_agents:
            memory_ranksum[key].append(mem_ranks[key])
            route_ranksum[key].append(rou_ranks[key])
            act_ranksum[key].append(act_ranks[key])

        _print(trial)
