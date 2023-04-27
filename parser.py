import re
import json
import graphviz


class Node:
    count = 0

    def __init__(self, label, style, week, parent=None, children=None):
        self.id = Node.count
        self.label = label
        self.style = style
        self.week = week
        self.parent = parent
        if children is None:
            children = []
        self.children = children
        Node.count += 1

def read_meta(name):
    f = open("meta/{}.txt".format(name), "r")
    name = ""
    term = ""
    orientation = ""
    styles = {}
    levels = {}
    nodes = []
    root = Node(label="", style="root", week=0, parent=None, children=nodes)

    parse_mode = None

    cur_node_parent = None
    cur_node_parent_depth = 0

    for line in f.readlines():
        if line.startswith("name:"):
            name = re.search(r"name: ([A-Za-z0-9\-_]+)", line).group(1)
        if line.startswith("term:"):
            term_match = re.search(r"term: ([A-Za-z0-9]+) ([0-9]+)", line)
            term = "{} {}".format(term_match.group(1), term_match.group(2))
        if line.startswith("orientation:"):
            orientation_match = re.search(r"orientation: ([A-Za-z]+) to ([A-Za-z]+)", line)
            orientation = "LR" if orientation_match.group(1) == "left" and orientation_match.group(2) == "right" else "RL"
        if line.startswith("styles:"):
            parse_mode = "STYLE"
            continue
        if line.startswith("student levels:"):
            parse_mode = "LEVEL"
            continue
        if line.startswith("nodes:"):
            parse_mode = "NODE"
            continue
        if line.startswith("end"):
            parse_mode = None

        if parse_mode == "STYLE":
            style_match = re.search(
                r"name: ([A-Za-z0-9]+), shape: ([A-Za-z]+), style: ([A-Za-z]+), fillcolor: #([A-Za-z0-9]+)", line)
            styles[style_match.group(1)] = {
                "shape": style_match.group(2),
                "style": style_match.group(3),
                "fillcolor": "#{}".format(style_match.group(4))
            }
        elif parse_mode == "LEVEL":
            level_match = re.search(r"([A-Za-z-_]+): #([A-Za-z0-9]+)", line)
            levels[level_match.group(1)] = "#{}".format(level_match.group(2))
        elif parse_mode == "NODE":
            node_match = re.search(r"(\s+)([A-Za-z0-9\-\s]+) \[([A-Za-z0-9]+), Week([0-9]+)", line)
            if len(node_match.group(1)) // 4 == 1:
                cur_node_parent = Node(node_match.group(2), node_match.group(3), node_match.group(4))
                nodes.append(cur_node_parent)
                cur_node_parent_depth = 1
            elif len(node_match.group(1)) // 4 < cur_node_parent_depth:
                cur_node_parent = cur_node_parent.parent
                cur_node_parent_depth -= 1
                cur_node_parent.parent.children.append(
                    Node(node_match.group(2), node_match.group(3), node_match.group(4), cur_node_parent))
            elif len(node_match.group(1)) // 4 == cur_node_parent_depth:
                new_children = Node(node_match.group(2), node_match.group(3), node_match.group(4), cur_node_parent.parent)
                cur_node_parent.parent.children.append(new_children)
                cur_node_parent = new_children
            elif len(node_match.group(1)) // 4 > cur_node_parent_depth:
                new_children = Node(node_match.group(2), node_match.group(3), node_match.group(4), cur_node_parent)
                cur_node_parent.children.append(new_children)
                cur_node_parent = new_children
                cur_node_parent_depth += 1

    f.close()

    root.label = name

    print("name: \n", name)
    print("term: \n", term)
    print("styles: \n", styles)
    print("levels: \n", levels)
    print("nodes: \n", nodes)

    return name, orientation, term, levels, styles, root

def to_json(name, term, levels, root):
    def nodes_to_json(node):
        nodes_json = {
            "id": node.id,
            "name": node.label,
            "parent": node.parent.label if node.parent else "null",
            "children": [nodes_to_json(c) for c in node.children],
            "data": {
                "week": node.week,
            }
        }
        return nodes_json

    json_out = {
        "name": name,
        "term": term,
        "levels": levels,
        "count": Node.count,
        "nodes": nodes_to_json(root)
    }

    print(json_out)
    with open('data/{}_parser_new.json'.format(name), 'w', encoding='utf-8') as json_out_file:
        json.dump(json_out, json_out_file, indent=4)

def to_dot(name, orientation, term, levels, styles, root, start_date=None, student_mastery=None):
    dot_out_file = open('data/{}.dot'.format(name), 'w', encoding='utf-8')
    dot_out = "digraph G { \n"
    dot_out += "	rankdir = LR; \n"

    def nodes_to_dot(node):
        nonlocal dot_out
        dot_out += "    node{}[label = \"{}\", shape = {}, style = {}, fillcolor = \"{}\"]; \n".format(node.id,
                                                                                               node.label,
                                                                                               styles[node.style]["shape"],
                                                                                               styles[node.style]["style"],
                                                                                               styles[node.style]["fillcolor"])
        for c in node.children:
            nodes_to_dot(c)

    def paths_to_dot(node):
        nonlocal dot_out
        for c in node.children:
            if orientation == "LR":
                dot_out += "    node{} -> node{}; \n".format(node.id, c.id)
            else:
                dot_out += "    node{} -> node{}; \n".format(c.id, node.id)
        for c in node.children:
            paths_to_dot(c)

    nodes_to_dot(root)
    dot_out += "    edge [arrowhead=\"none\"]; \n"
    paths_to_dot(root)

    dot_out += "} \n"

    print(dot_out)
    dot_out_file.write(dot_out)
    dot_out_file.close()

def to_svg(name):
    dot = graphviz.Source.from_file("data/{}.dot".format(name))
    dot.render(format="svg", outfile="data/{}.svg".format(name))

def generate_map(name):
    _, orientation, term, levels, styles, root = read_meta(name)
    to_dot(name, orientation, term, levels, styles, root)
    to_svg(name)
