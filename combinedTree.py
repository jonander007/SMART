#!/usr/bin/env python
# -*- coding: utf-8 -*-
from treelib import Tree as TreelibTree, Node as TreelibNode
from ipytree import Tree as IpytreeTree, Node as IpytreeNode
import ipywidgets as widgets
from IPython.display import display
from graphviz import Source, render
import subprocess, os, shutil


# Check if graphviz is installed
graphviz_ok = False
try:
	output = subprocess.check_output(['dot', '-V'])
	graphviz_ok = True
except FileNotFoundError:
	graphviz_ok = False

class CombinedTree:
    """
    CombinedTree structure combining the capabilities of treelib Tree with the widgets of ipytree Tree
    """
    def __init__(self, root='root'):
        self.treelib_tree = TreelibTree()
        self.ipytree_tree = IpytreeTree(
                multiple_selection=False,
                layout=widgets.Layout(width='100%'),
                )
        self.ipytree_root = IpytreeNode(root)
        self.ipytree_tree.add_node(self.ipytree_root)
        self.root = self.ipytree_root.name
        self.treelib_tree.create_node(self.root, self.root, data=self.ipytree_root)

    def _build_fresh_node(self, identifier):
        """Create a fresh IpytreeNode for identifier and all its descendants, updating treelib .data refs."""
        old_node = self.treelib_tree.get_node(identifier).data
        new_node = IpytreeNode(identifier)
        if old_node is not None:
            new_node.icon_style = getattr(old_node, 'icon_style', 'default')
        self.treelib_tree.get_node(identifier).data = new_node
        children = self.treelib_tree.children(identifier)
        new_node.nodes = tuple(self._build_fresh_node(c.identifier) for c in children)
        return new_node

    def _refresh_tree(self):
        """Rebuild the entire ipytree from treelib state with fresh nodes."""
        new_root = self._build_fresh_node(self.root)
        self.ipytree_root = new_root
        self.ipytree_tree.nodes = (new_root,)

    def change_icon_style(self, identifier, style):
        ipytree_node = self.get_ipytree_node(identifier)
        ipytree_node.icon_style = style

    def reset_icon_style(self):
        for identifier in self.get_node_names():
            self.change_icon_style(identifier, "default")

    def create_node(self, identifier, parent=None):
        """
        Create a new node with ID 'identifier' and parent 'parent'. If parent is None the node is added to the root.
        """
        ipytree_node = IpytreeNode(identifier)
        self.treelib_tree.create_node(identifier, identifier, parent, data=ipytree_node)
        self._refresh_tree()

    def remove_node(self, identifier):
        """
        Remove node with ID 'identifier'
        """
        if identifier != self.root:
            self.treelib_tree.remove_subtree(identifier)
            self._refresh_tree()

    def paste(self, parent, subtree):
        self.create_node(subtree.root, parent)
        for child in subtree.children(subtree.root):
            self.create_node(child.identifier, subtree.root)
            if len(subtree.is_branch(child.identifier)) > 0:
                subsubtree = subtree.subtree(child.identifier)
                self.paste(child.identifier, subsubtree)

    def move_node(self, identifier, new_parent):
        if identifier != self.root:
            subtree = self.treelib_tree.subtree(identifier)
            self.remove_node(identifier)
            self.paste(new_parent, subtree)

    def get_node_names(self, level=None):
        if level is None:
            nodes = [node.identifier for node in self.treelib_tree.all_nodes()]
        else:
            nodes = []
            for node in self.treelib_tree.nodes:
                if self.treelib_tree.level(node) == level:
                    nodes.append(node)
        return nodes

    def get_ipytree_node(self, identifier):
        return self.treelib_tree.get_node(identifier).data

    def get_treelib_node(self, identifier):
        return self.treelib_tree.get_node(identifier)

    def rename_treelib_node(self, old_identifier, new_identifier):
        self.treelib_tree.update_node(old_identifier,
                identifier=new_identifier, tag=new_identifier)

    def rename_ipytree_node(self, old_identifier, new_identifier):
        ipytree_node = self.get_ipytree_node(old_identifier)
        ipytree_node.name = new_identifier
        if old_identifier == self.root:
            self.root = new_identifier

    def rename_node(self, old_identifier, new_identifier):
        self.rename_ipytree_node(old_identifier, new_identifier)
        self.rename_treelib_node(old_identifier, new_identifier)

    def get_hierarchy(self):
        out = {}
        for criterion in self.treelib_tree.all_nodes():
            children = [node.identifier for node in self.treelib_tree.children(criterion.identifier)]
            if children:
                out[criterion.identifier] = children
        return out

    def to_dict(self):
        return self.treelib_tree.to_dict()

    def from_dict(self, data):
        for root, root_dict in data.items():
            if root != self.root:
                self.rename_node(self.root, root)
            children = [node.identifier for node in self.treelib_tree.children(root)]
            for child in children:
                self.remove_node(child)
            self.add_children(root_dict, root)

    def add_children(self, criteria_dict, parent):
        if 'children' in criteria_dict.keys():
            for subcriteria in criteria_dict['children']:
                if type(subcriteria) is dict:
                    subcriteria_name = list(subcriteria.keys())[0]
                    self.create_node(subcriteria_name, parent)
                    self.add_children(subcriteria[subcriteria_name], subcriteria_name)
                else:
                    subcriteria_name = subcriteria
                    self.create_node(subcriteria_name, parent)

    def __str__(self):
        return self.treelib_tree.__str__()

    def show(self):
        display(self.ipytree_tree)

    def plot(self, filename='tree'):
        """Render the tree.

        Returns the path of the generated file: a .png when Graphviz is
        available and the rendering succeeded, otherwise a .txt fallback.
        The caller must decide how to read it based on the extension, never
        on the module-level ``graphviz_ok`` flag (rendering can fail even
        when the ``dot`` binary is present).
        """
        filename = os.path.join('tmp', filename)
        png_file = filename + '.png'
        dot_file = filename + '.dot'
        if graphviz_ok:
            try:
                for stale in (png_file, dot_file, dot_file + '.png'):
                    if os.path.isfile(stale):
                        os.remove(stale)
                self.treelib_tree.to_graphviz(dot_file)
                out = None
                try:
                    # graphviz >= 0.20: outfile lets us control the name
                    out = render('dot', 'png', dot_file, outfile=png_file)
                except TypeError:
                    # older graphviz: writes to <filepath>.png
                    out = render('dot', 'png', dot_file)
                # Locate whatever was actually produced
                candidates = [c for c in (out, png_file, dot_file + '.png') if c]
                produced = next((c for c in candidates if os.path.isfile(c)), None)
                if produced is None:
                    raise FileNotFoundError('Graphviz produced no output file')
                if os.path.abspath(produced) != os.path.abspath(png_file):
                    shutil.copyfile(produced, png_file)
                return png_file
            except Exception as e:
                print(f'[SMART] Graphviz tree rendering failed ({e}); '
                      f'falling back to text tree.')
        if os.path.isfile(filename + '.txt'):
            os.remove(filename + '.txt')
        self.treelib_tree.save2file(filename + '.txt')
        return filename + '.txt'

    def observe(self, func, **kwargs):
        self.ipytree_tree.observe(func, **kwargs)
