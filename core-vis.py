import networkx as nx
import vtk
import math
import random
import argparse
import sys

ap = argparse.ArgumentParser()
#ap.add_argument("-l", "--neuron_config_lua", required=False, help="neuron config file (lua)")
#ap.add_argument("-n", "--neuron_config", required=False, help="neuron config file (converted to adjacency list)")
ap.add_argument("-f", "--core_data", required=True, help="data for core (probably called mpi-sampling-stats)")
ap.add_argument("-c", "--num_cores", required=True, help="number of cores on chip to visualize")
args = vars(ap.parse_args())

####
# turns out I don't need NeMo config file for core-level vis
# saving just in case I need this code for NN layered vis
#def read_config(filename):
#    cores = 0
#    neurons_per_core = 0
#    i = 0
#
#    out_file = filename + ".adj"
#    out = open(out_file, "w")
#
#    f = open(filename, "r")
#    for line in f:
#        neuron_flag = False
#        if i == 0:
#            cores = int(line.split("=")[1].strip())
#        elif i == 1:
#            neurons_per_core = int(line.split("=")[1].strip())
#        elif i == 2:
#            pass
#        elif i == 3:
#            neuron_flag = True
#            raw_neuron = line.split("{", 1)[1].split("{", 1)[1].strip()
#            print (raw_neuron)
#        else:
#            neuron_flag = True
#            raw_neuron = line.split("{", 1)[1].strip()
#        i += 1
#
#        if neuron_flag:
#            tokens = raw_neuron.split(",", 3)
#            coreid = int(tokens[1].split("=")[1].strip())
#            localid = int(tokens[2].split("=")[1].strip())
#            globalid = coreid * neurons_per_core + localid
#
#            connections = tokens[3].split("{")[1].split("}")[0].strip().split(",")
#
#            out.write(str(globalid) + " ")
#
#            out.write("\n")
#
#    return cores, neurons_per_core

#if "neuron_config_lua" in args:
#    read_config(args["neuron_config_lua"])


def create_core_grid(num_cores):
    points = vtk.vtkPoints().NewInstance()
    pos = {}
    x = 0
    y = 0
    z = 0

    dim = int(math.sqrt(num_cores))
    grid = nx.grid_graph(dim=[dim, dim])
    if num_cores != grid.number_of_nodes():
        sys.exit("number of cores does not equal number of nodes in generated graph!")

    for i in range(grid.number_of_nodes()):
        x += 10
        if i % 64 == 0:
            x = 0
            y += 10

        pos[i] = (x, y, z)
        points.InsertPoint(i, x, y, z)

    return points


def read_mpi_stats_data(filename):
    data = {}
    i = 0
    num_samples = 0

    f = open(filename, "r")
    for line in f:
        if i == 1:
            tokens = line.split(" ")
            num_samples = int(float(tokens[3])/float(tokens[1]))
        elif i > 1:
            tokens = line.split(" ")
            coreid = int(tokens[1])
            sample = int(tokens[2])
            metric = int(tokens[3])
            if coreid not in data:
                data[coreid] = [0 for x in range(num_samples)]
            data[coreid][sample] = metric
        i += 1

    return data, num_samples


def get_data_step(data, num_cores, step):
    step_arr = vtk.vtkIntArray().NewInstance()
    step_arr.SetName("NumSends")
    step_arr.SetNumberOfComponents(1)

    for i in range(num_cores):
        if i in data:
            step_arr.InsertValue(i, data[i][step])
            print(data[i][step])
        else:
            step_arr.InsertValue(i, 0)

    return step_arr


core_data, num_samples = read_mpi_stats_data(args["core_data"])
num_cores = int(args["num_cores"])
points = create_core_grid(num_cores)

# using the vtkGraph approach
graph = vtk.vtkMutableUndirectedGraph()
graph.SetNumberOfVertices(num_cores)
graph.SetPoints(points)


edge_geom = vtk.vtkGraphToPolyData()
edge_geom.SetInputData(graph)
edge_geom.Update()

polydata = edge_geom.GetOutput()
writer = vtk.vtkXMLPolyDataWriter()

for i in range(num_samples):
    cur_step = get_data_step(core_data, num_cores, i)
    polydata.GetPointData().AddArray(cur_step)

    writer.SetFileName("core-vtp/core" + str(i) + ".vtp")
    writer.SetInputData(polydata)
    writer.Write()
