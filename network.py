import networkx as nx
import vtk
import math
import random


# get routers and terminal lists from graph
def split_routers_terminals(G):
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


# split up edges into different lists
# assumes routers are lists of ints
def split_edges(G, routers, group_size):
    terminal_edges = []
    local_edges = []
    global_edges = []
    routerid_start = min(routers)

    for v1, v2 in G.edges:
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


# create my own slimfly graph layout
# returns a dictionary of positions keyed by node
def slimfly_layout(G, num_groups, group_size):
    pos = {}
    groupid = -1
    total_vertices = G.number_of_nodes()
    routers, terminals = split_routers_terminals(G)
    terminal_edges, local_edges, global_edges = split_edges(G, routers, group_size)
    routerid_start = min(routers)

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
        if (i - routerid_start) % router_group_size == 0:
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

    return pos


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


# set these to figure out router groups
# TODO change to program input args
router_group_size = 13
num_router_groups = 26

points = vtk.vtkPoints().NewInstance()
#type_arr = vtk.vtkIntArray().NewInstance()
#type_arr.SetName("NumSends")
#type_arr.SetNumberOfComponents(1)

# read in network connections from Graph XML format
G = nx.read_gexf("connection-data/sfly3042.gexf")

all_coords = slimfly_layout(G, num_router_groups, router_group_size)

routers, terminals = split_routers_terminals(G)
term_edges, local_edges, global_edges = split_edges(G, routers, router_group_size)

# now terminal_coords contains the correct (2d) coordinates for all terminals and routers
# input coords all terminals/routers
for nodeid, coords in all_coords.iteritems():
    coords = list(coords)
    # first check if this is a terminal or router
    if G.node[str(nodeid)]['viz']['color']['r'] == 255:
        # terminal
#        type_arr.InsertValue(nodeid, random.randint(0, 20))
        coords.append(2)
    elif G.node[str(nodeid)]['viz']['color']['g'] == 255:
        # router
#        type_arr.InsertValue(nodeid, random.randint(10, 200))
        coords.append(8)
    else:
        print("NO VALUE SAVED\n")
    x = coords[0]
    y = coords[1]
    z = coords[2]
    rad = math.pi/2
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
    #points.InsertPoint(nodeid, x, y, z)

# using the vtkGraph approach
graph = vtk.vtkMutableUndirectedGraph()
graph.SetNumberOfVertices(G.number_of_nodes())
graph.SetPoints(points)

for v1, v2 in term_edges:
    graph.LazyAddEdge(int(v1), int(v2))

for v1, v2 in local_edges:
    graph.LazyAddEdge(int(v1), int(v2))

for v1, v2 in global_edges:
    graph.LazyAddEdge(int(v1), int(v2))

edge_geom = vtk.vtkGraphToPolyData()
edge_geom.SetInputData(graph)
edge_geom.Update()

polydata = edge_geom.GetOutput()
writer = vtk.vtkXMLPolyDataWriter()

for i in range(100):
    cur_step = create_random_temporal_data(all_coords)
    polydata.GetPointData().AddArray(cur_step)

    writer.SetFileName("slimfly" + str(i) + ".vtp")
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

