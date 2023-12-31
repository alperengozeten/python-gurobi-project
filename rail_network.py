import gurobipy as gp
from gurobipy import GRB
import numpy as np

if __name__ == "__main__":
    # read the distances.txt file and store the distances in a numpy array
    distances = np.loadtxt("data/distances.txt").astype(np.int64)

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

    depot_node_distances = np.array(depot_node_distances, dtype=int)

    # read the assigned_depots to numpy array as integers
    X = np.loadtxt("data/assigned_depots.txt", dtype=int)

    # calculate the maximum hours train can travel on each path, by also considering the
    # distance between the depot and the starting node of the path and the distance between
    # the ending node of the path and the depot. The train can cycle on the path, but you
    # should include the distance between end node and start node to start another cycle.
    # The train can travel at most 20 hours a day.
    max_hours = []
    max_loops = []
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
        max_loops.append(k)

    W = []
    hour_lists = []
    for i in range(15):
        hour = 0
        assigned_depot = 0
        if X[i, 1] == 1:
            assigned_depot = 1
        ls = []

        for r in range(0, 21):
            ls.append([0] * 10)

        # add a list of 10 elements where every element is 0 except 9th element
        # if the path starts from depot 0 and 10th element if the path starts from depot 1
        if X[i, 0] == 1:
            ls[hour][8] = 1
        else:
            ls[hour][9] = 1

        hour += depot_node_distances[assigned_depot][paths[i][0]]

        for loop in range(max_loops[i]):
            for j in range(len(paths[i]) - 1):
                ls[hour][paths[i][j]] = 1

                hour += distances[paths[i][j]][paths[i][j + 1]]

            ls[hour][paths[i][-1]] = 1

            if (loop + 1) != max_loops[i]:
                hour += distances[paths[i][-1]][paths[i][0]]

        hour += depot_node_distances[assigned_depot][paths[i][-1]]
        if assigned_depot == 0:
            ls[hour][8] = 1
        else:
            ls[hour][9] = 1

        W.append(ls)

    # define parameter P such that $p_{ir}$: Binary parameter indicating if train $i$ is on some node
    # at time $r$ for $1 \leq i \leq 15$ and $1 \leq r \leq 20$ using W
    # add binary parameter p_ir for each path i and time r
    P = []
    for i in range(15):
        P.append([0] * 21)

    for i in range(15):
        for r in range(21):
            for j in range(10):
                if W[i][r][j] == 1:
                    P[i][r] = 1
                    break

    # define parameter Q such that $q_{ir}$: Binary parameter indicating if train $i$ is on some depot
    # at time $r$ for $1 \leq i \leq 15$ and $1 \leq r \leq 20$ using W
    # add binary parameter q_ir for each path i and time r
    Q = []
    for i in range(15):
        Q.append([0] * 21)

    for i in range(15):
        for r in range(1, 21):
            if W[i][r][8] == 1 or W[i][r][9] == 1:
                for m in range(r, 21):
                    Q[i][m] = 1

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

    # define $y_{ir}$: Binary variable indicating if train belonging to path $i$
    # is charged at time $r$ for $1 \leq i \leq 15$ and $0 \leq r \leq 20$.
    # add binary variable y_ir for each path i and time r
    y = model.addVars(15, 21, vtype=GRB.BINARY, name="y")

    # define $z_{ir}$: Variable indicating the number of hours passed since train
    # belonging to path $i$ is last charged, at time $r$ for $1 \leq i \leq 15$
    # and $0 \leq r \leq 20$.
    # add integer variable z_ir for each path i and time r
    z = model.addVars(15, 21, vtype=GRB.INTEGER, name="z")

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
        model.addConstr(expr == 1, f"a{i}")

    # add constraint $2 s_{k} \geq \sum_{i=1}^{15}d_{i}X_{ik}$ for $1 \leq k \leq 2$.
    # for each depot k, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for k in range(2):
        expr = gp.LinExpr()
        for i in range(15):
            expr += d[i] * X[i, k]
        model.addConstr(expr <= 2 * s[k], f"b{k}")

    # add constraint $3 t_{k} \geq \sum_{i=1}^{15}e_{i}X_{ik}$ for $1 \leq k \leq 2$.
    # for each depot k, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for k in range(2):
        expr = gp.LinExpr()
        for i in range(15):
            expr += e[i] * X[i, k]
        model.addConstr(expr <= 3 * t[k], f"c{k}")

    # add constraint $r_{j} \geq \sum_{i=1}^{15} y_{ir} w_{irj}$ for $1 \leq j \leq 8$ and $1 \leq r \leq 20$.
    # for each node j, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for j in range(8):
        for r_index in range(21):
            expr = gp.LinExpr()
            for i in range(15):
                expr += y[i, r_index] * W[i][r_index][j]
            model.addConstr(expr <= r[j], f"d{j}{r_index}")

    # add constraint $y_{ir} \leq e_{i}$ for $1 \leq i \leq 15$ and $0 \leq r \leq 20$.
    # for each path i and time r, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        for r_index in range(21):
            expr = gp.LinExpr()
            expr += y[i, r_index]
            model.addConstr(expr <= e[i], f"e{i}-{r_index}")

    # add constraint $y_{ir} \leq \sum_{j=1}^{10} w_{irj}$ for $1 \leq i \leq 15$ and $0 \leq r \leq 20$.
    # for each path i and time r, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        for r_index in range(21):
            expr = gp.LinExpr()
            expr += P[i][r_index]
            expr += Q[i][r_index]
            model.addConstr(expr >= y[i, r_index], f"f{i}-{r_index}")

    # add constraint $z_{i(r+1)} \geq z_{ir} + 1 - 20y_{i(r+1)}$ for $0 \leq i \leq 15$ and $0 \leq r \leq 19$.
    # for each path i and time r, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        for r_index in range(20):
            expr = gp.LinExpr()
            expr += z[i, r_index + 1] - z[i, r_index] - 1 + 20 * y[i, r_index + 1]
            model.addConstr(expr >= 0, f"g{i}-{r_index}")

    # add constraint $z_{i(r+1)} \leq z_{ir} + 1$ for $0 \leq i \leq 15$ and $0 \leq r \leq 19$.
    # for each path i and time r, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        for r_index in range(20):
            expr = gp.LinExpr()
            expr += z[i, r_index + 1] - z[i, r_index]
            model.addConstr(expr <= 1, f"h{i}-{r_index}")

    # add constraint $z_{ir} \leq 20(1-y_{ir})$ for $0 \leq i \leq 15$ and $0 \leq r \leq 20$.
    # for each path i and time r, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        for r_index in range(21):
            expr = gp.LinExpr()
            expr += z[i, r_index] + 20 * y[i, r_index]
            model.addConstr(expr <= 20, f"i{i}-{r_index}")

    # add constraint $z_{ir} \leq 8e_{i} + 20(1-e_{i}) + 20q_{ir}$ for $1 \leq i \leq 15$ and $0 \leq r \leq 20$.
    # for each path i and time r, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        for r_index in range(21):
            expr = gp.LinExpr()
            expr += z[i, r_index] - 8 * e[i] - 20 * (1 - e[i]) - 20 * Q[i][r_index]
            model.addConstr(expr <= 0, f"j{i}-{r_index}")

    # add constraint $z_{ir} \geq 0$ for $1 \leq i \leq 15$ and $0 \leq r \leq 20$.
    # for each path i and time r, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        for r_index in range(21):
            expr = gp.LinExpr()
            expr += z[i, r_index]
            model.addConstr(expr >= 0, f"l{i}-{r_index}")

    # add constraint $z_{i0}=0$ for $1 \leq i \leq 15$.
    # for each path i, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for i in range(15):
        expr = gp.LinExpr()
        expr += z[i, 0]
        model.addConstr(expr == 0, f"m{i}")

    # add the objective function $\min \sum_{i=1}^{15} (c_{eh} e_{i} + c_{dh} d_{i}) h_{i} + \sum_{i=1}^{15} (c_{e} e_{i} + c_{d} d_{i}) + \sum_{k=1}^{2} (c_{dc} t_{k} + c_{df} s_{k}) + \sum_{j=1}^{8} r_{j} c_{rc}$
    # create a linear expression
    # add the linear expression to the model
    expr = gp.LinExpr()
    for i in range(15):
        expr += (c_eh * e[i] + c_dh * d[i]) * max_hours[i] + (c_e * e[i] + c_d * d[i])
    for k in range(2):
        expr += (c_dc * t[k] + c_df * s[k])
    for j in range(8):
        expr += r[j] * c_rc

    # set the objective function
    model.setObjective(expr, GRB.MINIMIZE)

    # write the model to a file
    model.write("rail_network.lp")

    # optimize the model
    model.optimize()

    '''
    # model is infeasible, trace the infeasible constraints
    if model.status == GRB.INFEASIBLE:
        print("Model is infeasible")
        model.computeIIS()
        model.write("model.ilp")
        exit(0)'''

    # print the optimal solution
    print("Optimal solution:")
    for v in model.getVars():
        print(v.varName, v.x)
    print('Obj:', model.objVal)

    # print the number of fuel stations built on each depot
    print("Number of fuel stations built on each depot:")
    for k in range(2):
        print(f"Depot {k}: {s[k].x}")

    # print the number of charging stations built on each depot
    print("Number of charging stations built on each depot:")
    for k in range(2):
        print(f"Depot {k}: {t[k].x}")

    # print the number of charging stations built on each node
    print("Number of charging stations built on each node:")
    for j in range(8):
        print(f"Node {j}: {r[j].x}")

    # print the number of hours passed since train belonging to path i is last charged
    print("Number of hours passed since train belonging to path i is last charged:")
    for i in range(15):
        print(f"Path {i}: {z[i, 0].x}")

    # print the number of hours train can travel on each path
    print("Number of hours train can travel on each path:")
    for i in range(15):
        print(f"Path {i}: {max_hours[i]}")