import networkx as nx
import vtk
import math
import random
import argparse
import sys

ap = argparse.ArgumentParser()
ap.add_argument("-n", "--network", required=False, help="network to visualize")
ap.add_argument("-g", "--graphfile", required=True, help="graph ML file")
ap.add_argument("-r", "--routerfile", required=False, help="router data file")
ap.add_argument("-t", "--termfile", required=False, help="terminal data file")
ap.add_argument("-i", "--samp_interval", required=False, help="interval for sampling data")
ap.add_argument("-e", "--samp_end_time", required=False, help="simulation end time of sampling data")
ap.add_argument("-o", "--out_path", required=False, help="path in vtp-files to use")
ap.add_argument("-s", "--routers_per_group", required=False, help="num routers per group (sfly/dfly only)")
ap.add_argument("-p", "--num_groups", required=False, help="number of groups (sfly/dfly only)")
args = vars(ap.parse_args())


# get routers and terminal lists from graph
def sfly_split_routers_terminals(G):
    terminals = []
    routers = []
    for nodeid in G.nodes:
        if G.node[nodeid]['viz']['color']['r'] == 255:
            # terminal
            terminals.append(int(nodeid))
        elif G.node[nodeid]['viz']['color']['g'] == 255:
            # router
            routers.append(int(nodeid))
    return routers, terminals


# get routers and terminal lists from graph
def dfly_split_routers_terminals(G):
    terminals = []
    routers = []
    for nodeid in G.nodes:
        if G.node[nodeid]['viz']['color']['r'] == 255:
            # terminal
            terminals.append(int(nodeid))
        elif G.node[nodeid]['viz']['color']['g'] == 255:
            # router
            routers.append(int(nodeid))

    for i in range(len(routers)):
        routers[i] = codes_relative_id(routers[i], len(terminals))
    for i in range(len(terminals)):
        terminals[i] = codes_relative_id(terminals[i], len(terminals))

    return routers, terminals


def split_routers_terminals_id(G, num_terminals):
    terminals = []
    routers = []
    for nodeid in range(G.number_of_nodes()):
        if nodeid < num_terminals:
            # terminal
            terminals.append(nodeid)
        else:
            # router
            routers.append(nodeid)
    return routers, terminals


# split up edges into different lists
# assumes routers are lists of ints
def sfly_split_edges(g, routers, group_size):
    terminal_edges = []
    local_edges = []
    global_edges = []
    routerid_start = min(routers)

    for v1, v2 in g.edges:
        v1 = int(v1)
        v2 = int(v2)

        if v1 in routers and v2 in routers:
            # determine whether intra- or inter- link
            g1 = (v1 - routerid_start) / group_size
            g2 = (v2 - routerid_start) / group_size
            if g1 == g2:
                local_edges.append((v1, v2))
            else:
                global_edges.append((v1, v2))
        else:
            terminal_edges.append((v1, v2))

    return terminal_edges, local_edges, global_edges


# converts IDs to following format
# terminal ids = 0 to num_terminals - 1
# router ids = num_terminals to total_vertices - 1
def codes_relative_id(global_id, num_terminals):
    local_id = -1
    num_nwlp = 8
    num_term = 4
    num_rout = 1
    group_size = num_nwlp + num_term + num_rout

    codes_grp = global_id / group_size
    rem = global_id % group_size
    if rem < num_nwlp:
        print("Warning: found nw-lp id")  # nwlps unused, shouldn't happen
    elif rem < num_nwlp + num_term:
        local_id = codes_grp * num_term + (rem - num_nwlp)
    else:
        local_id = num_terminals + (codes_grp * num_rout + (rem - num_nwlp - num_term))
    #print("converting global id " + str(global_id) + " to local id " + str(local_id))

    return local_id


# split up edges into different lists
# assumes routers are lists of ints
# assumes ids have been converted to
def dfly_split_edges(g, routers, num_terminals, group_size):
    terminal_edges = []
    local_edges = []
    global_edges = []
    routerid_start = num_terminals

    for v1, v2 in g.edges:
        r1 = codes_relative_id(int(v1), num_terminals)
        r2 = codes_relative_id(int(v2), num_terminals)

        if r1 in routers and r2 in routers:
            # determine whether intra- or inter- link
            g1 = (r1 - routerid_start) / group_size
            g2 = (r2 - routerid_start) / group_size
            if g1 == g2:
                local_edges.append((r1, r2))
            else:
                global_edges.append((r1, r2))
        else:
            terminal_edges.append((r1, r2))

    return terminal_edges, local_edges, global_edges


# create my own slimfly graph layout
# returns a dictionary of positions keyed by node
def slimfly_layout(G, num_groups, group_size):
    pos = {}
    groupid = -1
    total_vertices = G.number_of_nodes()
    routers, terminals = sfly_split_routers_terminals(G)
    terminal_edges, local_edges, global_edges = sfly_split_edges(G, routers, group_size)
    routerid_start = min(routers)
    step_arr = vtk.vtkIntArray().NewInstance()
    step_arr.SetName("NodeType")
    step_arr.SetNumberOfComponents(1)

    if len(routers) != num_groups * group_size:
        print("WARNING: num_groups * group_size != num routers for slimfly layout")
        return pos

    # determine the center of each group in each subgraph
    subgraph = nx.Graph()
    for i in range(num_groups/2):
        subgraph.add_node(i)

    # only need to do for one subgraph, and just change y to -y in other subgraph
    subgraph_centers = nx.circular_layout(subgraph, center=[50, 100], dim=2, scale=120)
    group_centers = {}
    for id, coords in subgraph_centers.iteritems():
        coords1 = list(coords)
        group_centers[id] = coords1
        coords[1] = -coords[1]
        group_centers[id + num_groups/2] = coords

    # create group subgraphs to use circular_layout for coordinates
    group_graphs = {x: nx.Graph() for x in range(num_groups)}
    router_graphs = {x: nx.Graph() for x in range(routerid_start, total_vertices)}
    for i in range(routerid_start, total_vertices):
        if (i - routerid_start) % group_size == 0:
            groupid += 1
        group_graphs[groupid].add_node(i)
        router_graphs[i].add_node(i)

    # add in local edges for setting graph layout
    for v1, v2 in local_edges:
        grp = (v1 - routerid_start) / group_size
        group_graphs[grp].add_edge(v1, v2)

    # use circular layout and update center between each call
    group_coords = {}
    for i in range(num_groups):
        group_coords[i] = nx.circular_layout(group_graphs[i], scale=20, center=group_centers[i], dim=2)

    # throw our router coordinates into pos map
    for grp, gmap in group_coords.iteritems():
        for router, coords in gmap.iteritems():
            pos[router] = coords
            step_arr.InsertValue(router, 2)

    # add terminals and edges to router subgraphs created earlier
    for v1, v2 in terminal_edges:
        r = -1
        t = -1
        if v1 in terminals:
            t = v1
            r = v2
        elif v2 in terminals:
            t = v2
            r = v1

        if t >= 0:
            router_graphs[r].add_edge(r, t)

    # use each router's position to determine its terminals' positions
    router_coords = {}
    for router, rgraph in router_graphs.iteritems():
        rgraph.remove_node(router)
        router_coords[router] = nx.circular_layout(rgraph, scale=3, center=list(pos[router]), dim=2)

    # add terminal coordinates to pos map
    for router, tmap in router_coords.iteritems():
        for terminal, coords in tmap.iteritems():
            pos[terminal] = coords
            step_arr.InsertValue(terminal, 1)

    return pos, step_arr


# dragonfly ids based on CODES global LP ids
# i.e., will need to skip over the ids for nw-lps
def dragonfly_layout(G, num_groups, group_size):
    pos = {}
    groupid = -1
    total_vertices = G.number_of_nodes()
    routers, terminals = dfly_split_routers_terminals(G)
    terminal_edges, local_edges, global_edges = dfly_split_edges(G, routers, len(terminals), group_size)
    routerid_start = len(terminals)
    step_arr = vtk.vtkIntArray().NewInstance()
    step_arr.SetName("NodeType")
    step_arr.SetNumberOfComponents(1)

    if len(routers) != num_groups * group_size:
        print("WARNING: num_groups * group_size != num routers for dragonfly layout")
        return pos

    # determine the center of each group in each subgraph
    subgraph = nx.Graph()
    for i in range(num_groups/2):
        subgraph.add_node(i)

    # only need to do for one subgraph, and just change y to -y in other subgraph
    subgraph_centers = nx.circular_layout(subgraph, center=[0, 0], dim=2, scale=150)
    group_centers = {}
    for id, coords in subgraph_centers.iteritems():
        coords1 = list(coords)
        group_centers[id] = coords1
        coords[1] = -coords[1]
        group_centers[id + num_groups/2] = coords

    # create group subgraphs to use circular_layout for coordinates
    group_graphs = {x: nx.Graph() for x in range(num_groups)}
    router_graphs = {x: nx.Graph() for x in range(routerid_start, total_vertices)}
    for i in range(routerid_start, total_vertices):
        if (i - routerid_start) % group_size == 0:
            groupid += 1
        group_graphs[groupid].add_node(i)
        router_graphs[i].add_node(i)

    # add in local edges for setting graph layout
    for v1, v2 in local_edges:
        grp = (v1 - routerid_start) / group_size
        group_graphs[grp].add_edge(v1, v2)

    # get router coordinates
    group_coords = {}
    num_cols = 16
    num_rows = 6
    cell_width = 12
    router_idx = routerid_start

    for i in range(num_groups):
        group_coords[i] = {}
        center = group_centers[i]
        for j in range(num_rows):
            for k in range(num_cols):
                if i % 2 == 1:
                    x = center[0] + (k - num_cols/2) * cell_width
                    y = center[1] + (j - num_rows/2) * cell_width
                else:
                    y = center[1] + (k - num_cols/2) * cell_width
                    x = center[0] + (j - num_rows/2) * cell_width
                group_coords[i][router_idx] = [x, y]
                router_idx += 1

    # throw our router coordinates into pos map
    for grp, gmap in group_coords.iteritems():
        for router, coords in gmap.iteritems():
            pos[router] = coords
            step_arr.InsertValue(router, 2)

    # add terminals and edges to router subgraphs created earlier
    for v1, v2 in terminal_edges:
        r = -1
        t = -1
        if v1 in terminals:
            t = v1
            r = v2
        elif v2 in terminals:
            t = v2
            r = v1

        if t >= 0:
            router_graphs[r].add_edge(r, t)

    # use each router's position to determine its terminals' positions
    router_coords = {}
    for router, rgraph in router_graphs.iteritems():
        rgraph.remove_node(router)
        router_coords[router] = nx.circular_layout(rgraph, scale=3, center=list(pos[router]), dim=2)

    # add terminal coordinates to pos map
    for router, tmap in router_coords.iteritems():
        for terminal, coords in tmap.iteritems():
            pos[terminal] = coords
            step_arr.InsertValue(terminal, 1)

    return pos, step_arr


def fattree_layout(G, num_terminals):
    pos = {}
    l1_start = num_terminals
    l2_start = l1_start + 180
    l3_start = l2_start + 180

    radix = 36
    cn_per_router = radix / 2  # also same as router_per_pod
    step_arr = vtk.vtkIntArray().NewInstance()
    step_arr.SetName("NodeType")
    step_arr.SetNumberOfComponents(1)

    # start with L3
    l3_graph = nx.Graph()
    for i in range(l3_start, G.number_of_nodes()):
        l3_graph.add_node(i)

    l3_pos = nx.circular_layout(l3_graph, center=[0, 0], dim=2, scale=70)
    for key, coords in l3_pos.iteritems():
        coords = list(coords)
        coords.append(75)
        pos[key] = coords
        step_arr.InsertValue(key, 4)

    # set up L2
    l2_graph = nx.Graph()
    for i in range(l2_start, l3_start):
        l2_graph.add_node(i)

    l2_pos = nx.circular_layout(l2_graph, center=[0, 0], dim=2, scale=120)
    # use L2 coordinates to set up corresponding L1 coordinates
    # makes sure pods are lined up
    for key, coords in l2_pos.iteritems():
        l1_key = key - l2_start + l1_start
        coords1 = list(coords)
        if key % 2 == 0:
            coords1.append(30)
            coords1[0] *= .9
            coords1[1] *= .9
        else:
            coords1.append(20)
        coords1[0] *= 1.75
        coords1[1] *= 1.75
        pos[l1_key] = coords1
        step_arr.InsertValue(l1_key, 2)

        coords = list(coords)
        coords.append(50)
        pos[key] = coords
        step_arr.InsertValue(key, 3)

    # set up terminal positions
    router_graphs = {x: nx.Graph() for x in range(l1_start, l2_start)}
    term_idx = 0
    for i in range(l1_start, l2_start):
        l1_pos = pos[i][0:2]
        router_graphs[i].add_node(i)
        for j in range(cn_per_router):
            router_graphs[i].add_edge(i, term_idx)
            term_idx += 1
        term_pos = nx.circular_layout(router_graphs[i], center=l1_pos, dim=2, scale=5)
        for key, coords in term_pos.iteritems():
            if key < num_terminals:
                coords = list(coords)
                coords.append(1)
                pos[key] = coords
                step_arr.InsertValue(key, 1)

    return pos, step_arr


# create some random time step data to test animation
def create_random_temporal_data(all_coords):
    step_arr = vtk.vtkIntArray().NewInstance()
    step_arr.SetName("NumSends")
    step_arr.SetNumberOfComponents(1)

    for nodeid, coords in all_coords.iteritems():
        coords = list(coords)
        # first check if this is a terminal or router
        if G.node[str(nodeid)]['viz']['color']['r'] == 255:
            # terminal
            step_arr.InsertValue(nodeid, random.randint(0, 20))
        elif G.node[str(nodeid)]['viz']['color']['g'] == 255:
            # router
            step_arr.InsertValue(nodeid, random.randint(10, 200))

    return step_arr


def read_sim_data(filename, node_type, num_terminals, num_samples, samp_interval):
    data = {}

    f = open(filename, "r")
    isStart = True
    cols = []
    node_id = -1
    for line in f:
        if isStart:
            cols = line.split(",")
            isStart = False
        else:
            tokens = line.strip().split(",")
            if node_type == "router":
                node_id = num_terminals + int(tokens[cols.index("router_id")])
            elif node_type == "terminal":
                node_id = int(tokens[cols.index("terminal_id")])
            #end_time = float(tokens[cols.index("end_time")])
            idx = int(float(tokens[cols.index("end_time")])/samp_interval)
            if node_id not in data:
                data[node_id] = [0 for i in range(num_samples)]
            else:
                data[node_id][idx] = sum([int(i) for i in tokens[cols.index("end_time")+1:]])

    return data


def get_data_step(term_data, router_data, step):
    step_arr = vtk.vtkIntArray().NewInstance()
    step_arr.SetName("VC_Occupancy")
    step_arr.SetNumberOfComponents(1)

    for key, value in term_data.iteritems():
        step_arr.InsertValue(key, term_data[key][step])
    for key, value in router_data.iteritems():
        step_arr.InsertValue(key, router_data[key][step])

    return step_arr


def sfly_set_vtk_points_array(all_coords, G, routers, terminals):
    points = vtk.vtkPoints().NewInstance()
    for nodeid, coords in all_coords.iteritems():
        coords = list(coords)
        # first check if this is a terminal or router
        if G.node[str(nodeid)]['viz']['color']['r'] == 255:
            # terminal
            coords.append(2)
        elif G.node[str(nodeid)]['viz']['color']['g'] == 255:
            # router
            coords.append(8)
        else:
            print("NO VALUE SAVED\n")

        x = coords[0]
        y = coords[1]
        z = coords[2]
        rad = 0
        translation = 0
        if nodeid in routers:
            if nodeid - min(routers) < (max(routers) + 1 - min(routers))/2:
                rad = math.pi / 2
                translation = 30
            else:
                rad = 3 * math.pi / 2
                translation = -30
        else:
            if nodeid - min(terminals) < (max(terminals) + 1 - min(terminals))/2:
                rad = math.pi / 2
                translation = 30
            else:
                rad = 3 * math.pi / 2
                translation = -30
        points.InsertPoint(nodeid, x, (y * math.cos(rad) - z * math.sin(rad)) + translation, y * math.sin(rad) + z * math.cos(rad))
    return points


def dfly_set_vtk_points_array(all_coords, routers, terminals):
    points = vtk.vtkPoints().NewInstance()
    for nodeid, coords in all_coords.iteritems():
        coords = list(coords)
        # first check if this is a terminal or router
        if nodeid in terminals:
            coords.append(2)
        elif nodeid in routers:
            coords.append(8)
        else:
            print("NO VALUE SAVED\n")

        x = coords[0]
        y = coords[1]
        z = coords[2]
        rad = 0
        translation = 0
        if nodeid in routers:
            if nodeid - min(routers) < (max(routers) + 1 - min(routers))/2:
                rad = math.pi / 2
                translation = 50
            else:
                rad = 3 * math.pi / 2
                translation = -50
        else:
            if nodeid - min(terminals) < (max(terminals) + 1 - min(terminals))/2:
                rad = math.pi / 2
                translation = 50
            else:
                rad = 3 * math.pi / 2
                translation = -50
        x1 = x
        y1 = (y * math.cos(rad) - z * math.sin(rad)) + translation
        z1 = y * math.sin(rad) + z * math.cos(rad)

        points.InsertPoint(nodeid, x1, y1, z1)
    return points


def ft_set_vtk_points_array(all_coords):
    points = vtk.vtkPoints().NewInstance()
    for nodeid, coords in all_coords.iteritems():
        points.InsertPoint(nodeid, coords[0], coords[1], coords[2])

    return points


def data_check(data, entities_start, entities_end, num_samples):
    for i in range(entities_start, entities_end):
        if i not in data:
            data[i] = [0 for _ in range(num_samples)]
    return data


# set these to figure out router groups
# TODO change to program input args
router_group_size = int(args["routers_per_group"])
num_router_groups = int(args["num_groups"])

num_samples = 1
flythrough_flag = False
if args["routerfile"] is None or args["termfile"] is None:
    flythrough_flag = True

# read in network connections from Graph XML format
print("reading graph file...")
G = nx.read_gexf(args["graphfile"])
print("done")

all_coords = {}
routers = []
terminals = []
node_arr = vtk.vtkIntArray()
filename_out = "vtp-files/"
if args["out_path"] is not None:
    filename_out += args["out_path"] + "/"

if flythrough_flag:
    filename_out += "flythrough/" + args["network"]
else:
    filename_out += args["network"] + "/" + args["network"]
print("creating layout for visualization...")
if args["network"] == "slimfly":
    all_coords, node_arr = slimfly_layout(G, num_router_groups, router_group_size)
    routers, terminals = sfly_split_routers_terminals(G)
elif args["network"] == "fattree":
    #G = nx.convert_node_labels_to_integers(G)
    all_coords, node_arr = fattree_layout(G, 3240)
    routers, terminals = split_routers_terminals_id(G, 3240)
elif args["network"] == "dragonfly":
    all_coords, node_arr = dragonfly_layout(G, num_router_groups, router_group_size)
    routers, terminals = dfly_split_routers_terminals(G)
    #sys.exit("ERROR: dragonfly has not been implemented yet")
else:
    sys.exit("ERROR: --network type should be one of the following: slimfly, fattree, dragonfly")
print("done")

router_data = {}
terminal_data = {}
if not flythrough_flag:
    num_samples = int(args["samp_end_time"])/int(args["samp_interval"])
    print("reading router data...")
    router_data = read_sim_data(args["routerfile"], "router", len(terminals), num_samples, int(args["samp_interval"]))
    #router_data = data_check(router_data, len(terminals), G.number_of_nodes(), num_samples)
    print("done\nreading terminal data...")
    terminal_data = read_sim_data(args["termfile"], "terminal", len(terminals), num_samples, int(args["samp_interval"]))
    #terminal_data = data_check(terminal_data, 0, len(terminals), num_samples)
    print("done\n")
else:
    flythrough_flag = True

# using the vtkGraph approach
graph = vtk.vtkMutableUndirectedGraph()
graph.SetNumberOfVertices(G.number_of_nodes())

# now terminal_coords contains the correct (2d) coordinates for all terminals and routers
# input coords all terminals/routers
if args["network"] == "slimfly":
    points = sfly_set_vtk_points_array(all_coords, G, routers, terminals)
    graph.SetPoints(points)
    term_edges, local_edges, global_edges = sfly_split_edges(G, routers, router_group_size)
    for v1, v2 in term_edges:
        graph.LazyAddEdge(int(v1), int(v2))

    for v1, v2 in local_edges:
        graph.LazyAddEdge(int(v1), int(v2))

    for v1, v2 in global_edges:
        graph.LazyAddEdge(int(v1), int(v2))
elif args["network"] == "fattree":
    points = ft_set_vtk_points_array(all_coords)
    graph.SetPoints(points)
    for v1, v2 in G.edges:
        graph.LazyAddEdge(int(v1), int(v2))
elif args["network"] == "dragonfly":
    points = dfly_set_vtk_points_array(all_coords, routers, terminals)
    graph.SetPoints(points)
    term_edges, local_edges, global_edges = dfly_split_edges(G, routers, len(terminals), router_group_size)
    for v1, v2 in term_edges:
        graph.LazyAddEdge(int(v1), int(v2))

    for v1, v2 in local_edges:
        graph.LazyAddEdge(int(v1), int(v2))

    for v1, v2 in global_edges:
        graph.LazyAddEdge(int(v1), int(v2))

    #sys.exit("ERROR: dragonfly has not been implemented yet")
else:
    sys.exit("ERROR: --network type should be one of the following: slimfly, fattree, dragonfly")


edge_geom = vtk.vtkGraphToPolyData()
edge_geom.SetInputData(graph)
edge_geom.Update()

polydata = edge_geom.GetOutput()
polydata.GetPointData().AddArray(node_arr)
writer = vtk.vtkXMLPolyDataWriter()

print("creating VTP files")
for i in range(num_samples):
    if not flythrough_flag:
        cur_step = get_data_step(terminal_data, router_data, i)
        polydata.GetPointData().AddArray(cur_step)

    writer.SetFileName(filename_out + str(i) + ".vtp")
    writer.SetInputData(polydata)
    writer.Write()



###############################
### old way of doing things
# instead of one large graphs of all terminals and routers
# turn into a hierarchy of graphs
# first separate nodes in G into routers and terminals
#routers, terminals = split_routers_terminals(G)
#
## create a new graph for each router and its terminals
#router_graphs = {x: nx.Graph() for x in routers}
#
#for router, rgraph in router_graphs.iteritems():
#    rgraph.name = int(router)
#    rgraph.add_node(router)
#
#intra_edges = []
#inter_edges = []
#term_edges = []
#routerid_start = min(routers)
#num_groups = len(routers) / router_group_size
#for v1, v2 in G.edges:
#    v1 = int(v1)
#    v2 = int(v2)
#    t = -1
#    r = -1
#    if v1 in terminals:
#        t = v1
#        r = v2
#    elif v2 in terminals:
#        t = v2
#        r = v1
#
#    if v1 not in terminals and v2 not in terminals:
#        # determine whether intra- or inter- link
#        g1 = (v1 - routerid_start) / router_group_size
#        g2 = (v2 - routerid_start) / router_group_size
#        if g1 == g2:
#            intra_edges.append((v1, v2))
#        else:
#            inter_edges.append((v1, v2))
#
#    if t > 0:
#        router_graphs[r].add_edge(r, t)
#        term_edges.append((t, r))
#
#print("length of term_edges: " + str(len(term_edges)))
#print("length of intra_edges: " + str(len(intra_edges)))
#print("length of inter_edges: " + str(len(inter_edges)))
#
## create new graph for each router group
##group_graphs = {x: nx.Graph() for x in range(num_groups)}
#
##grp_id = -1
##for i in range(routerid_start, num_net_nodes):
##    if i % router_group_size == 0:
##        grp_id += 1
##    group_graphs[grp_id].add_node(router_graphs[i])
#
##for v1, v2 in intra_edges:
##    grp = (v1 - routerid_start) / router_group_size
##    grp2 = (v1 - routerid_start) / router_group_size
##    group_graphs[grp].add_edge(router_graphs[v1], router_graphs[v2])
#
#
## how to do connections between different groups?
#
## create the two bipartite subgraphs
##subgraphs = {x: nx.Graph() for x in range(2)}
##for i in range(num_groups):
##    sg_id = -1
##    if i < num_groups/2:
##        sg_id = 0
##    else:
##        sg_id = 1
##    subgraphs[sg_id].add_node(group_graphs[i])
#
#
## now create one graph of all router subgraphs
#full_graph = nx.Graph()
##for key, ggraph in group_graphs.iteritems():
#for key, ggraph in router_graphs.iteritems():
#    ggraph.name = int(key)
#    full_graph.add_node(ggraph)
#
#for v1, v2 in intra_edges:
#    full_graph.add_edge(router_graphs[v1], router_graphs[v2])
#
#for v1, v2 in inter_edges:
#    full_graph.add_edge(router_graphs[v1], router_graphs[v2])
#
## add in edges for routers
##for v1, v2 in G.edges:
##    if v1 not in terminals and v2 not in terminals:
##        # need to use specific router graph to add edges between subgraphs, not their names
##        full_graph.add_edge(router_graphs[int(v1)], router_graphs[int(v2)])
#
## first set the coordinates of the each group
##group_coords = nx.circular_layout(full_graph, dim=2, scale=4)
#router_coords = nx.circular_layout(full_graph, dim=2, scale=4)
#
## use group_coords to determine coords of each router in each group
##router_coords = {}
#terminal_coords = {}
#for ggraph, coords in router_coords.iteritems():
#    key = ggraph.name
#    fixed_pos = list(coords)
#    terminal_coords[key] = nx.circular_layout(ggraph, center=fixed_pos, dim=2, scale=2)
#
## use router_coords to determine where to place the teriminals
##for groupid, gmap in router_coords.iteritems():
##    for rgraph, coords in gmap.iteritems():
##        key = rgraph.name
##        fixed_pos = {key: coords}
##        terminal_coords[key] = nx.spring_layout(rgraph, fixed=[key], pos=fixed_pos, dim=2)
#

