import gurobipy as gp
from gurobipy import GRB
import numpy as np


if __name__ == '__main__':
    model = gp.Model("mip1")

    # for each pair of the 15 paths and 2 depots, create a binary variable
    # X_{ik} 1 if the path i uses the depot k, 0 otherwise
    x = model.addVars(15, 2, vtype=GRB.BINARY, name="x")

    # add the constraint \sum_{i=1}^{15} X_{ij} \geq 5 for each depot j
    # for each depot j, create a linear expression
    # add the linear expression to the model
    # add the constraint to the model
    for j in range(2):
        expr = gp.LinExpr()
        for i in range(15):
            expr += x[i, j]
        model.addConstr(expr >= 5, f"c{j}")

    y = []
    z = []
    # create a numpy array of parameters Y_{ij} for each pair of paths i and node j
    # which indicates if the path i starts from node j by reading from paths.txt
    with open("data/paths.txt", "r") as f:
        lines = f.readlines()
        for line in lines:
            # remove the '\n' at the end of the line if exists
            if line[-1] == '\n':
                line = line[:-1]

            # get the index of ':' in the line
            idx = line.index(':')

            # create a list with only (line[idx + 2]-'A')th element as 1 and rest as 0
            y.append([0]*8)
            y[-1][ord(line[idx + 2])-ord('A')] = 1

            # create a list with only (line[-1]-'A')th element as 1 and rest as 0
            z.append([0]*8)
            z[-1][ord(line[-1])-ord('A')] = 1

    d = []
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
            d.append(list(map(int, line[idx + 2:].split('-'))))

    # convert the lists to numpy arrays
    y = np.array(y)
    z = np.array(z)
    d = np.array(d)

    # add the constraint \sum_{j=1}^{2} X_{ij} = 1 for each path i
    # for each path i, create a linear expression
    for i in range(15):
        expr = gp.LinExpr()
        for j in range(2):
            expr += x[i, j]
        model.addConstr(expr == 1, f"p{i}")

    # add the constraint \sum_{i=1}^{15} X_{ik} Y_{ij} \leq 3 for each node j and depot k
    # for each node j and depot k, create a linear expression
    for j in range(8):
        for k in range(2):
            expr = gp.LinExpr()
            for i in range(15):
                expr += x[i, k] * y[i, j]
            model.addConstr(expr <= 3, f"n{j}d{k}")

    # define the min objective function \min \sum_{i=1}^{15} \sum_{j=1}^{8} \sum_{k=1}^{2} (Y_{ij} d_{jk}X_{ik} + Z_{ij} d_{jk}X_{ik})
    # create a linear expression
    expr = gp.LinExpr()
    for i in range(15):
        for j in range(8):
            for k in range(2):
                expr += (y[i, j] + z[i, j]) * x[i, k] * d[k, j]

    # add the linear expression to the model
    model.setObjective(expr, GRB.MINIMIZE)

    # print the model
    model.write("model.lp")

    # optimize the model
    model.optimize()

    X_paths = []
    Y_paths = []

    # print the optimal solution
    print("Optimal solution:")
    for v in model.getVars():
        # get the index of ',' in the variable name
        idx = v.varName.index(',')
        path = v.varName[2:idx]
        val = int(path) + 1

        if v.varName[-2] == '0' and v.x == 1: # depot X
            X_paths.append(val)
        elif v.varName[-2] == '1' and v.x == 1: # depot Y
            Y_paths.append(val)

        print(v.varName, v.x)
    print('Obj:', model.objVal)

    print("Assigned Trains To Depot X:" + str(X_paths))
    print("Assigned Trains To Depot Y:" + str(Y_paths))
