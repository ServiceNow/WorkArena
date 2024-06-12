import numpy as np


class KnapsackInstanceGenarator:
    """
    Generates a knapsack instance with the given number of items and maximum capacity, and solves it.
    The instance is guaranteed to have a unique optimal solution in "random" or "single_item" mode .

    Args:
    - random: Random number generator
    - num_items: Number of items
    - max_capacity: Maximum capacity of the knapsack
    - mode: Mode of generation. Choice of "random", "trivial", "single_item", "single_item_uniform", "n_items"
        - random: Randomly generate the instance and return it; guaranteed to have a unique optimal solution
        - trivial: Generate a trivial instance with all items fitting in the knapsack; return the instance
        - single_item: Generate an instance where the optimal solution has only one item
        - n_items: Generate an instance with all items having uniform weight and value; n items fitting in the knapsack
        - single_item_uniform: Generate an instance with all items having uniform weight and value; optimal solution has only one item and it can be any
    - num_items_in_solution: Number of items in the optimal solution. Required for "n_items" mode.
    - default_return: Default return value for investments having uniform weight and value. Required for "n_items" and "single_item_uniform" modes.
    """

    def __init__(
        self,
        random: np.random,
        num_items: int,
        max_capacity: int,
        mode: str = "random",
        num_items_in_solution: int = None,
        default_return: int = 100000,
    ):
        self.random = random
        self.num_items = num_items
        self.max_capacity = max_capacity
        self.mode = mode
        self.num_items_in_solution = num_items_in_solution
        self.default_return = default_return

    def get_instance(self):
        if self.mode in ["random", "trivial"]:
            return self.generate_and_solve_knapsack_instance()
        elif self.mode == "single_item":
            return self.generate_single_item_knapsack_instance()
        elif self.mode in ["single_item_uniform", "n_items"]:
            return self.generate_uniform_knapsack_instance()
        else:
            raise ValueError(f"Invalid mode {self.mode} for knapsack instance generation")

    def generate_and_solve_knapsack_instance(self):
        """
        Generates a knapsack instance with the given number of items and maximum capacity, and solves it.
        Used to generate instances for the "random" and "trivial" mode.
        Returns:
        - investments: List of tuples (cost, investment_return) for each investment
        - max_return: Maximum return achievable with optimal solution
        - selected_indices: Indices of the investments selected in the optimal solution
        """

        assert self.mode in [
            "random",
            "trivial",
        ], f"Mode {self.mode} is invalid for instance generation with generate_and_solve_knapsack_instance"

        multiple_solutions = True
        while multiple_solutions:
            # Generate knapsack instance...
            investments = []
            min_cost = self.max_capacity // (self.num_items * 2)
            max_cost = (
                self.max_capacity // 2
                if self.mode == "random"
                else self.max_capacity // self.num_items
            )
            for _ in range(self.num_items):
                cost = self.random.randint(min_cost, max_cost)
                # Ensure that investments yield positive returns
                investment_return = self.random.randint(
                    self.max_capacity // 2, self.max_capacity // 2 + 40000
                )
                investments.append((cost, investment_return))

            total_cost = sum([investments[i][0] for i in range(self.num_items)])
            # Skip trivial instances where all items fit in the knapsack
            if self.mode == "random" and total_cost <= self.max_capacity:
                continue

            if self.mode == "random":
                # ...Solve it...
                max_return, num_optimal_solutions, selected_indices = self.solve_knapsack(
                    investments, self.max_capacity
                )
                # ...and check if there are multiple solutions
                multiple_solutions = num_optimal_solutions > 1
            else:
                selected_indices = list(range(self.num_items))
                max_return = sum([investments[i][1] for i in selected_indices])
                multiple_solutions = False

        return investments, max_return, selected_indices

    def generate_single_item_knapsack_instance(self):
        """Generate knapsack instance where the optimal solution contains only one item
        Returns:
        - investments: List of tuples (cost, investment_return) for each investment
        - max_investment_return: Investment return of the selected investment in the optimal solution
        - selected_indices: Index of the selected investment in the optimal solution
        """
        assert (
            self.mode == "single_item"
        ), f"Mode {self.mode} is invalid for instance generation with generate_single_item_knapsack_instance"

        # Ensure that the optimal solution contains only one item
        min_cost = self.max_capacity // 2 + 1
        max_cost = self.max_capacity - 1

        max_investment_return = 0
        max_investment_index = 0

        # Generate knapsack instance...
        investments = []
        for i in range(self.num_items):
            cost = self.random.randint(min_cost, max_cost)
            investment_return = self.random.randint(max_cost, 2 * max_cost)

            # Ensure that the optimal solution contains only one item
            while investment_return == max_investment_return:
                investment_return = self.random.randint(max_cost, 2 * max_cost)

            if investment_return > max_investment_return:
                max_investment_return = investment_return
                max_investment_index = i

            investments.append((cost, investment_return))

        return investments, max_investment_return, [max_investment_index]

    def generate_uniform_knapsack_instance(self):
        """Generate knapsack instance where all items have the same cost and return
        Returns:
        - investments: List of tuples (cost, investment_return) for each investment
        - max_return: Maximum return achievable with optimal solution
        - selected_indices=None: No need to return selected indices as all items have the same cost and return. The validation code should check that
          the optimal solution contains a subset of the items of the right length.
        """
        assert self.mode in [
            "single_item_uniform",
            "n_items",
        ], f"Mode {self.mode} is invalid for instance generation with generate_n_items_knapsack_instance"
        items_in_solution = self.num_items_in_solution if self.mode == "n_items" else 1

        # Ensure that the optimal solution contains the specified number of items
        item_weight = self.max_capacity // (items_in_solution + 1) + 1
        # Generate knapsack instance...
        investments = [(item_weight, self.default_return) for _ in range(self.num_items)]

        return investments, self.default_return * items_in_solution, None

    def solve_knapsack(self, investments, max_capacity):
        """Solves the knapsack problem using dynamic programming"""
        num_investments = len(investments)

        # Initialize DP table for maximum return and number of ways
        dp = [[(0, 0) for _ in range(max_capacity + 1)] for _ in range(num_investments + 1)]

        for i in range(1, num_investments + 1):
            cost, return_ = investments[i - 1]
            for w in range(max_capacity + 1):
                if cost <= w:
                    # If adding the current investment yields a higher return, update the cell
                    if return_ + dp[i - 1][w - cost][0] > dp[i - 1][w][0]:
                        dp[i][w] = (return_ + dp[i - 1][w - cost][0], 1)
                    # If it yields the same return, add the number of ways from the cell without the current investment
                    elif return_ + dp[i - 1][w - cost][0] == dp[i - 1][w][0]:
                        dp[i][w] = (dp[i - 1][w][0], dp[i - 1][w][1] + dp[i - 1][w - cost][1])
                    # If it yields a lower return, keep the old maximum return and number of ways
                    else:
                        dp[i][w] = dp[i - 1][w]
                else:
                    dp[i][w] = dp[i - 1][w]

        # Retrieve the maximum return and the number of ways to achieve it
        max_return, num_ways = dp[num_investments][max_capacity]

        # Retrieve the indices of the selected investments
        selected_indices = []
        w = max_capacity
        for i in range(num_investments, 0, -1):
            if dp[i][w] != dp[i - 1][w]:
                selected_indices.append(i - 1)
                w -= investments[i - 1][0]

        return max_return, num_ways, selected_indices
