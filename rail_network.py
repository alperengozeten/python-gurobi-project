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
    X = np.loadtxt("data/assigned_depots.txt", dtype=int)

    # calculate the maximum hours train can travel on each path, by also considering the
    # distance between the depot and the starting node of the path and the distance between
    # the ending node of the path and the depot. The train can cycle on the path, but you
    # should include the distance between end node and start node to start another cycle.
    # The train can travel at most 20 hours a day.
    max_hours = []
    for i in range(15):
        # 0 for X, 1 for Y from assigned_depots
        assigned_depot = 0
        if X[i, 1] == 1:
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

    # define cost constants and make them final
    c_e = 750000
    c_d = 250000
    c_dc = 1000000
    c_df = 800000
    c_rc = 350000
    c_eh = 20000
    c_dh = 100000

    # create the model
    model = gp.Model("rail_network")

    # define $s_{k}$, variable indicating the number of fuel stations built on
    # depot $k$ for $1 \leq k \leq 2$.
    # add integer variable s_k for each depot k
    s = model.addVars(2, vtype=GRB.INTEGER, name="s")

    # define $t_{k}$, variable indicating the number of charging stations built
    # on depot $k$ for $1 \leq k \leq 2$.
    # add integer variable t_k for each depot k
    t = model.addVars(2, vtype=GRB.INTEGER, name="t")

    # add binary variable d_i for each path i which indicates if diesel train
    # is used on path i
    d = model.addVars(15, vtype=GRB.BINARY, name="d")

    # add binary variable e_i for each path i which indicates if electric train
    # is used on path i
    e = model.addVars(15, vtype=GRB.BINARY, name="e")

    # define $r_{j}$, variable indicating the number of charging stations built
    # on node $j$ for $1 \leq j \leq 8$.
    # add integer variable r_j for each node j
    r = model.addVars(8, vtype=GRB.INTEGER, name="r")

    # add constraint $e_{i} + d_{i} = 1$ for $ 1 \leq i \leq 15$.
    # for each path i, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        expr = gp.LinExpr()
        expr += e[i] + d[i]
        model.addConstr(expr == 1, f"c{i}")

    # add constraint $2 s_{k} \geq \sum_{i=1}^{15}d_{i}X_{ik}$ for $1 \leq k \leq 2$.
    # for each depot k, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for k in range(2):
        expr = gp.LinExpr()
        for i in range(15):
            expr += d[i] * X[i, k]
        model.addConstr(expr <= 2 * s[k], f"c{k}")


    # write the model to a file
    model.write("rail_network.lp")