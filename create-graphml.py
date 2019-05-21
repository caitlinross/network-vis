import argparse
import csv
import networkx as nx

ap = argparse.ArgumentParser()
#ap.add_argument("-n", "--network", required=False, help="network to visualize")
ap.add_argument("-c", "--connections_file", required=True, help="connections csv file")
ap.add_argument("-f", "--codes_conf_file", required=True, help="codes network conf file")
args = vars(ap.parse_args())

DRAGONFLY_CUSTOM = 0

network = -1
num_groups = 0
num_routers = 0
num_terminals = 0

def get_value(line):
    return line.split("=")[1].strip().strip('";')

def read_codes_conf():
    global num_groups
    global num_routers
    global num_terminals
    global network

    reps = 0
    rep_router = 0
    f = open(args["codes_conf_file"], "r")
    params_flag = False
    for line in f:
        if line.startswith("PARAMS"):
            params_flag = True
        if "modelnet_order" in line:
            if "dragonfly_custom" in line:
                network = DRAGONFLY_CUSTOM
        if "num_groups" in line:
            num_groups = int(get_value(line))
        if "repetitions" in line:
            reps = int(get_value(line))
        if params_flag == False and "router" in line:
            rep_router = int(get_value(line))
        if "num_cns_per_router" in line:
            num_terminals = int(get_value(line))

    num_routers = reps * rep_router
    num_terminals *= num_routers
    f.close()
    print(num_terminals)
    print(num_routers)


def topology_connections():
    f = open(args["connections_file"], "r")
    data = csv.DictReader(f)
    routers = {}
    inter_edges = {}
    intra_edges = {}
    full_graph = nx.Graph()
    for row in data:
        src_gid = int(row["src_gid"])
        src_type = int(row["src_type"])
        src_type_id = int(row["src_type_id"])
        src_group = int(row["src_group_id"])
        dest_gid = int(row["dest_gid"])
        dest_type = int(row["dest_type"])
        dest_type_id = int(row["dest_type_id"])
        dest_group = int(row["dest_group_id"])

        if src_type == 1:
            #if dest_gid not in routers:
                #routers[dest_gid] = nx.Graph()
                #routers[dest_gid].add_node(dest_gid, lptype="router", router_id=dest_type_id, group_id=dest_group)
                #full_graph.add_node(dest_gid, subgraph=routers[dest_gid])
            #routers[dest_gid].add_node(src_gid, lptype="terminal", term_id=src_type_id, group_id=src_group)
            #routers[dest_gid].add_edge(src_gid, dest_gid, link="term")

            full_graph.add_node(dest_gid, lptype="router", router_id=dest_type_id, group_id=dest_group)
            full_graph.add_node(src_gid, lptype="terminal", term_id=src_type_id, group_id=src_group)
            full_graph.add_edge(src_gid, dest_gid, link="term")

        if src_type == 0 and dest_type == 0:
            if src_group == dest_group:
                if src_gid not in intra_edges:
                    intra_edges[src_gid] = []
                intra_edges[src_gid].append(dest_gid)
            else:
                if src_gid not in inter_edges:
                    inter_edges[src_gid] = []
                inter_edges[src_gid].append(dest_gid)

    for r1, r_list in intra_edges.items():
        for r2 in r_list:
            full_graph.add_edge(r1, r2, link="local")

    for r1, r_list in inter_edges.items():
        for r2 in r_list:
            full_graph.add_edge(r1, r2, link="global")


    print(full_graph.number_of_nodes())
    print(full_graph.number_of_edges())
    f.close()
    return full_graph


read_codes_conf()

full_graph = topology_connections()
nx.write_graphml(full_graph, "dragonfly-custom.gexf", prettyprint=True)
