import gurobipy as gp
from gurobipy import GRB
import numpy as np

if __name__ == "__main__":
    # read the distances.txt file and store the distances in a numpy array
    distances = np.loadtxt("data/distances.txt")

    print(distances.shape)

    # read the paths.txt file and store the paths in a list
    paths = []
    with open("data/paths.txt", "r") as f:
        lines = f.readlines()
        for line in lines:
            # remove the '\n' at the end of the line if exists
            if line[-1] == '\n':
                line = line[:-1]

            # get the index of ':' in the line
            idx = line.index(':')

            # create a list starting from the index after ':' to the end of the line
            # which are separated by '-'
            line = line[idx + 2:].split('-')

            line = [ord(x) - ord('A') for x in line]

            paths.append(line)

    depot_node_distances = []
    # create a numpy array of parameters d_{jk} for each pair of depot j and node k which
    # indicates the distance between the depot j and node k by reading from depot_node_distances.txt
    with open("data/depot_node_distances.txt", "r") as f:
        lines = f.readlines()
        for line in lines:
            # remove the '\n' at the end of the line if exists
            if line[-1] == '\n':
                line = line[:-1]

            # get the index of ':' in the line
            idx = line.index(':')

            # read the part after ':' as a list which are separated by '-'
            depot_node_distances.append(list(map(int, line[idx + 2:].split('-'))))

    depot_node_distances = np.array(depot_node_distances)

    # read the assigned_depots to numpy array as integers
    assigned_depots = np.loadtxt("data/assigned_depots.txt", dtype=int)

    # calculate the maximum hours train can travel on each path, by also considering the
    # distance between the depot and the starting node of the path and the distance between
    # the ending node of the path and the depot. The train can cycle on the path, but you
    # should include the distance between end node and start node to start another cycle.
    # The train can travel at most 20 hours a day.
    max_hours = []
    for i in range(15):
        # 0 for X, 1 for Y from assigned_depots
        assigned_depot = 0
        if assigned_depots[i, 1] == 1:
            assigned_depot = 1

        remaining_hour = 20 - depot_node_distances[assigned_depot][paths[i][0]] - depot_node_distances[assigned_depot][paths[i][-1]]
        print(remaining_hour)

        # find the length of the path
        path_length = 0
        for j in range(len(paths[i]) - 1):
            path_length += distances[paths[i][j]][paths[i][j + 1]]

        # find largest k such that k * path_length + (k-1) * (start_node - end_node) <= remaining_hour
        k = 0
        while k * path_length + (k - 1) * (distances[paths[i][0]][paths[i][-1]]) <= remaining_hour:
            k += 1
        k = k - 1

        max_hour = (k * path_length + (k - 1) * (distances[paths[i][0]][paths[i][-1]])
                    + depot_node_distances[assigned_depot][paths[i][0]] +
                    depot_node_distances[assigned_depot][paths[i][-1]])

        max_hours.append(max_hour)

