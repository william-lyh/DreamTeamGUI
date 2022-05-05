import sys
import re
import json
from datetime import datetime
from Node import Node

"""
Dream Team Parser
@Version: DEV
@Copy Right:

    - Parser:
        (C) 2022 University of California, Berkeley - ACE Lab

    - Web GUI - Modifications:
        Copyright 2022 University of California, Berkeley - ACE Lab

        Permission to use, copy, modify, and/or distribute this software for any purpose
        with or without fee is hereby granted, provided that the above copyright notice
        and this permission notice appear in all copies.

        THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
        REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
        FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
        INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
        OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
        TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
        THIS SOFTWARE.

    - Web GUI - Interactive d3.js tree diagram
        Copyright 2022 github.com/d3noob

        Permission is hereby granted, free of charge, to any person obtaining a copy of
        this software and associated documentation files (the "Software"), to deal in the
        Software without restriction, including without limitation the rights to use, copy,
        modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
        and to permit persons to whom the Software is furnished to do so, subject to the
        following conditions:

        The above copyright notice and this permission notice shall be included in all copies
        or substantial portions of the Software.

        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
        INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
        PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
        FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
        OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
        DEALINGS IN THE SOFTWARE.

    - Web GUI - D3.js Framework
        Copyright 2010-2021 Mike Bostock

        Permission to use, copy, modify, and/or distribute this software for any purpose
        with or without fee is hereby granted, provided that the above copyright notice
        and this permission notice appear in all copies.

        THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
        REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
        FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
        INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
        OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
        TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
        THIS SOFTWARE.


Parser for Dream Team GUI - a Concept Map
"""


class DreamTeamParser:
    PRE_INFO_PATTERN = r'[\s]*rankdir = (.+)'
    NODE_PATTERN = r'[\s]*node(.*)\['
    PATH_PATTERN = r'[\s]*node([\d]+)[\s]*->[\s]*node([\d]+);[\s]*\n'
    MULTI_PATH_MATCH_PATTERN = re.compile(r'[\s]*\{(node(\d)+,\s)+node(\d)+\}[\s]*->[\s]*node([\d]+);[\s]*\n')
    MULTI_PATH_EXTRACT_PATTERN = re.compile(r'node(\d+)')
    WEEK_CEILING = 0

    def __init__(self, file_name, priority_cutoff):
        self.file_name = file_name
        self.dtm = None
        self.name = ""
        self.term = ""
        self.levels = None
        self.priority_cutoff = priority_cutoff
        self.dot_lines = None
        self.nodes = []
        self.filtered_nodes = []
        self.paths = []
        self.filtered_paths = []
        self.classes = {}
        self.rankdir = ""
        self.root = None
        self.log = ""
        self.log += "{}: DreamTeamParser initialized with dot file target {}.dot and " \
                    "priority level {}\n".format(datetime.now(), self.file_name, self.priority_cutoff)

    def read_json(self):
        self.dtm = open("meta/{}_DTM.json".format(self.file_name), "r")
        dtm_data = json.load(self.dtm)
        self.name = dtm_data["name"]
        self.term = dtm_data["term"]
        self.levels = dtm_data["levels"]
        self.rankdir = dtm_data["rankdir"]
        self.classes = dtm_data["styles"]
        for node in dtm_data["nodes"]:
            self.add_node(node["name"], node["label"], node["priority"], node["week"], node["class"])
        for path in dtm_data["edges"]:
            start = path["from"]
            for end in path["to"]:
                self.paths.append((start, end))
        self.post_filter_all_paths()
        self.find_root()
        return

    def read_dot(self, dot_name):
        self.name = self.file_name
        self.classes["default"] = {
            "shape": "ellipse",
            "style": "filled",
            "fillcolor": "#e0e0e0"
        }
        with open("data/{}.dot".format(dot_name)) as dot_file:
            self.dot_lines = dot_file.readlines()
        for i in range(len(self.dot_lines)):
            dot_line = self.dot_lines[i]
            if re.compile(DreamTeamParser.PRE_INFO_PATTERN).match(dot_line):
                self.rankdir = re.search(DreamTeamParser.PRE_INFO_PATTERN, dot_line).groups()[0]
            elif re.compile(DreamTeamParser.NODE_PATTERN).match(dot_line):
                self.read_node(dot_line)
            elif re.compile(DreamTeamParser.PATH_PATTERN).fullmatch(dot_line):
                self.read_path(dot_line)
            elif re.compile(DreamTeamParser.MULTI_PATH_MATCH_PATTERN).fullmatch(dot_line):
                self.read_multi_path(dot_line)
        self.log += "{}: Parsing completed \n".format(datetime.now())
        self.log += "{}: Parsed {} nodes \n".format(
            datetime.now(), len(self.nodes))
        self.log += "{}: Parsed {} paths \n".format(
            datetime.now(), len(self.paths))
        self.log += "{}: Begin verify paths \n".format(datetime.now())
        self.post_filter_all_paths()
        self.log += "{}: Parsed and verified {} paths \n".format(
            datetime.now(), len(self.paths))

    def read_node(self, dot_line):
        try:
            node_label = re.search(r'label\s*=\s*"\s*([^"]+)\s*"', dot_line).groups()[0]
        except:
            try:
                node_label = re.search(r'label\s*=\s*<\s*(.+)\s*>', dot_line).groups()[0]
            except:
                print(dot_line)
                raise RuntimeError

        node_label = re.sub(r'<([^>]+)>', "", node_label)
        node_label = re.sub(r'\s+$', "", node_label)
        node_label = re.sub(r'\\n', "", node_label)

        node_color_matching = re.search(r'fillcolor = "?([#A-Za-z\d\s]+)"?', dot_line)
        if node_color_matching:
            node_color = node_color_matching.groups()[0]
        else:
            node_color = "#e0e0e0"
        node_style_matching = re.search(r'style = "?([A-Za-z\d\s]+)"?', dot_line)
        if node_style_matching:
            node_style = node_style_matching.groups()[0]
        else:
            node_style = "filled"
        node_shape_matching = re.search(r'shape = "?([A-Za-z\d\s]+)"?', dot_line)
        if node_shape_matching:
            node_shape = node_shape_matching.groups()[0]
        else:
            node_shape = "ellipse"
        for style_name, style in self.classes.items():
            if style["shape"] == node_shape and style["style"] == node_style and style["fillcolor"] == node_color:
                self.add_node(len(self.nodes), node_label, 0, 0, style_name)
                return
        self.classes["style{}".format(len(self.classes) + 1)] = {
            "shape": node_shape,
            "style": node_style,
            "fillcolor": node_color
        }
        self.add_node(len(self.nodes), node_label, 0, 0, "style{}".format(len(self.classes)))

    def expand_node(self, name):
        if name < len(self.nodes):
            return
        else:
            difference = name - len(self.nodes) + 1
            self.nodes += [None] * difference
            self.filtered_nodes += [None] * difference

    def add_node(self, name, text, priority, week, style_class):
        self.expand_node(name)
        self.nodes[name] = Node(name, text, priority, week, style_class)
        if text.lower().strip() == self.name.lower().strip():
            self.root = self.nodes[name]
        if priority <= self.priority_cutoff:
            self.filtered_nodes[name] = Node(name, text, priority, week, style_class)
        else:
            self.log += "{}: Node{} with priority level {} ignored under cutoff {}\n".format(
                datetime.now(), name, priority, self.priority_cutoff)
        return

    def read_path(self, dot_line):
        path_info = re.search(DreamTeamParser.PATH_PATTERN, dot_line).groups()
        self.paths.append((int(path_info[0]), int(path_info[1])))

    def read_multi_path(self, dot_line):
        path_info = re.findall(DreamTeamParser.MULTI_PATH_EXTRACT_PATTERN, dot_line)
        for i in range(len(path_info)-1):
            self.paths.append((int(path_info[i]), int(path_info[-1])))

    def post_filter_all_paths(self):
        filtered_paths = []
        for i in range(len(self.paths)):
            start, end = self.paths[i]
            if start >= len(self.nodes) or end >= len(self.nodes):
                self.log += "{}: Path {} to {} refers to undefined node(s) \n".format(
                    datetime.now(), start, end)
            else:
                self.nodes[start].add_child(self.nodes[end])
                self.nodes[end].add_parent(self.nodes[start])
                if self.filtered_nodes[start] is not None and self.filtered_nodes[end] is not None:
                    filtered_paths.append((self.nodes[start], self.nodes[end]))
                    self.filtered_nodes[start].add_child(self.filtered_nodes[end])
                    self.filtered_nodes[end].add_parent(self.filtered_nodes[start])
                else:
                    self.log += "{}: Path {} to {} refers to undefined node(s) \n".format(
                        datetime.now(), start, end)
        self.filtered_paths = filtered_paths

    def find_root(self):
        roots = []
        for node in self.filtered_nodes:
            if node is not None:
                if node.get_parent_count() == 0:
                    roots.append(node)
        self.filtered_root = Node(name=0, text=self.file_name, priority=0, week=DreamTeamParser.WEEK_CEILING, style_class="default")
        self.filtered_nodes[0] = self.filtered_root
        for child in roots:
            self.filtered_root.add_child(child)
            self.filtered_paths.append((self.filtered_root, child))

        roots = []
        for node in self.nodes:
            if node is not None:
                if node.get_parent_count() == 0:
                    roots.append(node)
        self.root = Node(name=0, text=self.file_name, priority=0, week=DreamTeamParser.WEEK_CEILING, style_class="default")
        self.nodes[0] = self.root
        self.filtered_nodes[0] = self.root
        for child in roots:
            self.root.add_child(child)
            self.paths.append((0, child.get_name()))

    def to_json(self):
        nodes_json = []
        for node in self.filtered_nodes:
            if node is not None:
                node_json = {'name': str(node.get_name()),
                             'label': node.get_text(),
                             'week': node.get_week()}
                if node.get_week() > DreamTeamParser.WEEK_CEILING:
                    DreamTeamParser.WEEK_CEILING = node.get_week()
                nodes_json.append(node_json)
        paths_json = []
        for path in self.filtered_paths:
            path_json = {'start': str(path[0].get_name()),
                         'end': str(path[1].get_name())}
            paths_json.append(path_json)
        all_data_json = {'nodes': nodes_json, 'paths': paths_json}
        with open('data/{}.json'.format(self.file_name), 'w', encoding='utf-8') as json_file:
            json.dump(all_data_json, json_file, indent=4)
        self.log += "{}: Wrote to JSON; File titled {}.json\n".format(
            datetime.now(), self.file_name)

    def to_json_meta(self):
        meta_json = {
            "name": self.name,
            "term": "",
            "rankdir": self.rankdir,
            "styles": self.classes,
            "levels": {
                "not-learned": "#000000",
                "unfamiliar": "#B2BEB5",
                "new": "#FFFF00",
                "intermediate": "#FFA500",
                "proficient": "#228B22"
            },
            "nodes": [],
            "edges": []
        }
        for node in self.nodes:
            if node == self.root:
                continue
            meta_json["nodes"].append({
                "name": node.get_name(),
                "label": node.get_text(),
                "week": node.get_week(),
                "class": node.get_style_class(),
                "priority": node.get_priority()
            })
        for path in self.paths:
            if self.root and self.root.get_name() in path:
                continue
            start_node_found = False
            for meta_json_path in meta_json["edges"]:
                if meta_json_path["from"] == path[0]:
                    meta_json_path["to"].append(path[1])
                    start_node_found = True
            if not start_node_found:
                meta_json["edges"].append({
                    "from": path[0],
                    "to": [path[1]]
                })
        with open('meta/{}_DTM_PARSED.json'.format(self.file_name), 'w', encoding='utf-8') as json_file:
            json.dump(meta_json, json_file, indent=4)

    def to_json_data(self):
        json_data = {
            "name": self.name,
            "term": self.term,
            "levels": self.levels,
            "count": len(self.nodes),
            "nodes": self.json_tree_generator(self.filtered_root)
        }
        with open('data/{}.json'.format(self.file_name), 'w', encoding='utf-8') as json_file:
            json.dump(json_data, json_file, indent=4)
        self.log += "{}: Wrote to JSON; File titled {}.json\n".format(
            datetime.now(), self.file_name)

    def json_tree_generator(self, node):
        node_json = {
            "id": str(node.get_name()),
            "name": node.get_text(),
            "parent": "null",
            "children": [],
            "data": {
                "week": node.get_week()
            }
        }
        for child in node.get_children():
            child_json = self.json_tree_generator(child)
            child_json["parent"] = node_json["name"]
            node_json["children"].append(child_json)
        return node_json

    def write_dot(self):
        dot = "digraph G {\n"
        dot += "\trankdir = {}\n".format(self.rankdir)
        for node in self.nodes:
            if node is not None:
                style_class = self.classes[node.get_style_class()]
                shape, style, fillcolor = style_class["shape"], style_class["style"], style_class["fillcolor"]
                dot += '''\tnode{}[label = "{}", shape = {}, style = {}, fillcolor = "{}"];\n'''.format(node.get_name(),
                                                                                                        node.get_text(),
                                                                                                        shape,
                                                                                                        style,
                                                                                                        fillcolor)
        for path in self.paths:
            dot += "\tnode{} -> node{};\n".format(path[0], path[1])
        dot += "}\n"
        with open('data/{}_DTP_DOT.dot'.format(self.file_name), 'w', encoding='utf-8') as dot_file:
            dot_file.write(dot)

    def write_log(self):
        with open('data/{}_DTP_log.txt'.format(self.file_name), 'w', encoding='utf-8') as log_file:
            log_file.write(self.log)
        print(self.log)
        print("{}: Wrote to log file; "
              "File titled {}_parser_log.txt".format(datetime.now(), self.file_name))

    def close_files(self):
        self.dtm.close()

    def parse(self):
        self.read_json()
        self.to_json_data()
        self.write_dot()
        self.write_log()
        self.close_files()


if __name__ == '__main__':
    DTP = DreamTeamParser(file_name=sys.argv[1], priority_cutoff=int(sys.argv[2]))
    '''
    DTP.read_dot("CS10")
    DTP.to_json_meta()
    '''
    DTP.parse()

