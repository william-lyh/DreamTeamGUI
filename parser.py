import re
import json
import os
import datetime
import graphviz
from collections import OrderedDict


class Node:
    count = 0

    def __init__(self, label, style, week, link, parent=None, children=None):
        self.id = Node.count
        self.label = label
        self.style = style
        self.week = int(week)
        self.link = link
        self.parent = parent
        if children is None:
            children = []
        self.children = children
        Node.count += 1


def read_meta(name):
    Node.count = 0
    f = open("meta/{}.txt".format(name), "r")
    name = ""
    term = ""
    orientation = ""
    start_date = []
    styles = {}
    class_levels = {}
    student_levels = OrderedDict()
    nodes = []
    root = Node(label="", style="root", week=0, link="", parent=None, children=nodes)

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
            orientation = "LR" if orientation_match.group(1) == "left" and orientation_match.group(
                2) == "right" else "RL"
        if line.startswith("start date:"):
            date_match = re.search(r"start date: (\d{4}) (\d{2}) (\d{2})", line)
            start_date.extend([int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))])
        if line.startswith("styles:"):
            parse_mode = "STYLE"
            continue
        if line.startswith("class levels:"):
            parse_mode = "CLASS_LEVEL"
            continue
        if line.startswith("student levels:"):
            parse_mode = "STUDENT_LEVEL"
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
        elif parse_mode == "CLASS_LEVEL":
            level_match = re.search(r"\s*([A-Za-z-_\s]+): #([A-Za-z0-9]+)", line)
            class_levels[level_match.group(1)] = "#{}".format(level_match.group(2))
        elif parse_mode == "STUDENT_LEVEL":
            level_match = re.search(r"\s*([A-Za-z-_\s]+): #([A-Za-z0-9]+)", line)
            student_levels[level_match.group(1)] = "#{}".format(level_match.group(2))
        elif parse_mode == "NODE":
            node_match = re.search(r"(\s+)([A-Za-z0-9\-\s]+) \[([A-Za-z0-9]+), Week([0-9]+), link=\"(.+)\"]", line)
            if len(node_match.group(1)) // 4 == 1:
                cur_node_parent = Node(node_match.group(2), node_match.group(3), node_match.group(4),
                                       node_match.group(5))
                nodes.append(cur_node_parent)
                cur_node_parent_depth = 1
            elif len(node_match.group(1)) // 4 < cur_node_parent_depth:
                cur_node_parent = cur_node_parent.parent
                cur_node_parent_depth -= 1
                cur_node_parent.parent.children.append(
                    Node(node_match.group(2), node_match.group(3), node_match.group(4), node_match.group(5),
                         cur_node_parent))
            elif len(node_match.group(1)) // 4 == cur_node_parent_depth:
                new_children = Node(node_match.group(2), node_match.group(3), node_match.group(4), node_match.group(5),
                                    cur_node_parent.parent)
                cur_node_parent.parent.children.append(new_children)
                cur_node_parent = new_children
            elif len(node_match.group(1)) // 4 > cur_node_parent_depth:
                new_children = Node(node_match.group(2), node_match.group(3), node_match.group(4), node_match.group(5),
                                    cur_node_parent)
                cur_node_parent.children.append(new_children)
                cur_node_parent = new_children
                cur_node_parent_depth += 1

    f.close()

    root.label = name

    '''
    print("name: \n", name)
    print("term: \n", term)
    print("start date: \n", start_date)
    print("styles: \n", styles)
    print("class levels: \n", class_levels)
    print("student levels: \n", student_levels)
    print("nodes: \n", nodes)
    '''

    return name, orientation, start_date, term, class_levels, student_levels, styles, root


def to_json(name, term, class_levels, student_levels, root):
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
        "class levels": class_levels,
        "student levels": student_levels,
        "count": Node.count,
        "nodes": nodes_to_json(root)
    }

    print(json_out)
    with open('data/{}_parser_new.json'.format(name), 'w', encoding='utf-8') as json_out_file:
        json.dump(json_out, json_out_file, indent=4)


def to_dot(name, token, student_mastery, orientation, start_date, term, class_levels, student_levels, styles, root):
    current_week = datetime.date.today().isocalendar()[1] - \
                   datetime.date(start_date[0], start_date[1], start_date[2]).isocalendar()[1]
    dot_out_file = open('data/{}_{}.dot'.format(name, token), 'w', encoding='utf-8')
    dot_out = "digraph G { \n"
    dot_out += "	rankdir = LR; \n"

    def nodes_to_dot(node):
        nonlocal dot_out
        if len(student_mastery) >= node.id != 0:
            mastery_color = list(student_levels.items())[int(student_mastery[node.id - 1])][1]
        else:
            mastery_color = "black"
        dot_out += "    " \
                   "node{}[label = \"{}\", " \
                   "shape = {}, style = {}, " \
                   "fillcolor = \"{}\", " \
                   "color = \"{}\", " \
                   "penwidth = 3, " \
                   "href = \"{}\", " \
                   "target=\"_blank\"]; \n".format(
            node.id,
            node.label,
            styles[node.style]["shape"],
            styles[node.style]["style"],
            styles[node.style]["fillcolor"],
            mastery_color,
            node.link)
        for c in node.children:
            nodes_to_dot(c)

    def paths_to_dot(node):
        nonlocal dot_out
        for c in node.children:
            if c.week < current_week:
                color = class_levels["Taught"]
            else:
                color = class_levels["Not Taught"]
            if orientation == "LR":
                dot_out += "    node{} -> node{} [penwidth = 3, color = \"{}\"]; \n".format(node.id, c.id, color)
            else:
                dot_out += "    node{} -> node{} [penwidth = 3, color = \"{}\"]; \n".format(c.id, node.id, color)
        for c in node.children:
            paths_to_dot(c)

    nodes_to_dot(root)
    dot_out += "    edge [arrowhead=\"none\"]; \n"
    paths_to_dot(root)

    dot_out += "} \n"

    # print(dot_out)
    dot_out_file.write(dot_out)
    dot_out_file.close()


def to_svg(name, token):
    dot = graphviz.Source.from_file("data/{}_{}.dot".format(name, token))
    dot.render(format="svg", cleanup=True, outfile="data/{}_{}.svg".format(name, token))


def generate_map(name, token, student_mastery):
    print("Log: {} {} -- {}".format(name, token, student_mastery))
    name, orientation, start_date, term, class_levels, student_levels, styles, root = read_meta(name)
    to_dot(name, token, student_mastery, orientation, start_date, term, class_levels, student_levels, styles, root)
    to_svg(name, token)


# generate_map("CS10", "", "322113200")
