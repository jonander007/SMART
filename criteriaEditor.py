#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/criteriaEditor.py
import copy
import ipywidgets as widgets
from IPython.display import display, HTML, Javascript
from graphviz import Source
from .combinedTree import CombinedTree
from .constants import section_label_style, tab_titles, arisdf
from .utilities import make_default_tree
from .titleAndHelp import TitleAndHelp

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Monday Jul 01, 2024 11:03:49 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Thursday Dec 19, 2024 16:29:08 CET'

#    TODO: 
#           Add things to do here

TAB = 2
TAB_TITLE = tab_titles[TAB]

cols_to_drop = ['Acronym', 'Full name']

if arisdf is not None:
    aris_criteria_list = arisdf.drop(cols_to_drop, axis=1).columns.to_list()
else:
    aris_criteria_list = []

class CriteriaEditor():
    def __init__(self, logger, default=None):
        self.logger = logger
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Initializing')

        self.select_ipytree_node = None
        if default:
            self.tree = make_default_tree(default)
        else:
            self.tree = make_default_tree('empty')
        self.root = self.tree.root
        self.descriptions_dict = {node:'' for node in self.tree.get_node_names()}

        self.title = TitleAndHelp('Edit the hierarchy of criteria and subcriteria', 'docs/help_criteriaEditor.html')

        self.addButton=widgets.Button(
            description='Add New',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Add a new Criterion',
            style={'description_width': 'initial'},
            #  layout=widgets.Layout(
                #  width='50%',
                #  ),
            icon='plus-square' # (FontAwesome names without the `fa-` prefix)
        )
        self.editButton=widgets.Button(
            description='Edit Selected',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Edit the selected Criterion',
            style={'description_width': 'initial'},
            #  layout=widgets.Layout(
                #  width='50%',
                #  ),
            icon='pen-square' # (FontAwesome names without the `fa-` prefix)
        )
        self.removeButton=widgets.Button(
            description='Remove Selected',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Remove selected Criterion and its Subcriteria',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='95%'),
            icon='minus-square' # (FontAwesome names without the `fa-` prefix)
        )
        #  self.name = widgets.Text(description='Criterion')
        self.name = widgets.Combobox(
            options=aris_criteria_list,
            disabled=False,
            description='Criteria',
                )
        self.parent = widgets.Combobox(
            options=self.tree.get_node_names(),
            disabled=False,
            description='Parent',
                )
        self.description = widgets.Textarea(
                placeholder='Enter a description for the criterion',
                description='Description',
                layout=widgets.Layout(width='99%')
                )
        self.nodeInfo = widgets.VBox([
            widgets.HBox([self.name, self.parent]),
            self.description,
            widgets.HBox([self.addButton, self.editButton])
            #  self.addButton
            ],
            layout=widgets.Layout(align_items='center')
                #  width='80%')
            )

        self.treebox = widgets.VBox(
                [self.tree.ipytree_tree, self.removeButton],
                layout=widgets.Layout(align_items='center')
                ) 

        self.globalbox = widgets.HBox([self.nodeInfo, self.treebox])
        self.links = []
        self.tree.observe(self.on_select_change, names='selected_nodes')
        #  self.name.observe(self.on_text_change)
        self.addButton.on_click(self.addCriteria)
        self.editButton.on_click(self.editCriteria)
        self.removeButton.on_click(self.removeCriteria)

        self.allWidgets = widgets.VBox([
                        self.title.allWidgets,
                        self.globalbox
                            ])

    def get_all_outputs(self):
        data = {
                tab_titles[2]: self.tree.to_dict(),
                'Descriptions': self.descriptions_dict
                }
        return data

    def set_all_values(self, data):
        self.tree.from_dict(data[tab_titles[2]])
        self.parent.options = self.tree.get_node_names()
        self.root = self.tree.root
        self.allWidgets.children = [
                        #  self.title.allWidgets,
                        #  #  widgets.HBox([self.tree.ipytree_tree,]), 
                        #  self.tree.ipytree_tree,
                        #  widgets.HBox([self.name, self.addButton, self.removeButton]),
                        self.title.allWidgets,
                        widgets.HBox([self.nodeInfo,
                            widgets.VBox([
                                self.tree.ipytree_tree,
                                self.removeButton])
                            ])
                        #  self.tree.ipytree_tree,
                        #  widgets.HBox([self.addButton, self.removeButton]),
                        ]
        if 'Descriptions' in data.keys():
            self.descriptions_dict = {node:data['Descriptions'][node] for node in self.tree.get_node_names()}
        else:
            self.descriptions_dict = {node:'' for node in self.tree.get_node_names()}

    def editCriteria(self, b):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Editing Criteria')
        self.tree.reset_icon_style()
        if len(self.tree.ipytree_tree.selected_nodes) > 0:
            selected = self.tree.ipytree_tree.selected_nodes[0]
            if selected.name == self.root:
                old_parent = ''
            else:
                old_parent = self.tree.treelib_tree.parent(selected.name).identifier
            name = self.name.value
            parent = self.parent.value
            description = self.description.value
            # If node has change, rename it
            if selected.name != name:
                # Update key in the descriptions_dict
                self.descriptions_dict[name] = self.descriptions_dict.pop(selected.name)
                # Rename node
                self.tree.rename_node(selected.name, name)
                # If the node was the root update root in self
                if selected.name == self.root:
                    self.root = name
            # If parent has changed, move the node to the new parent
            if old_parent != parent:
                if parent not in self.tree.get_node_names():
                    # Create the parent node in the root
                    self.tree.create_node(parent, self.root)
                    self.tree.change_icon_style(parent, 'warning')
                    # Create empty entry for parent in descriptions_dict
                    self.descriptions_dict[parent] = ''
                self.tree.move_node(name, parent)
            # Update description_dict
            self.descriptions_dict[name] = description
            # Change icon to reflect changes
            self.tree.change_icon_style(name, 'warning')
            # Update options for parent combobox
            self.parent.options = self.tree.get_node_names()

    def addCriteria(self, b):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Adding Criteria')
        #  selectedNode = self.tree.ipytree_tree.selected_nodes[0]
        #  name = self.get_new_name(selectedNode)
        name = self.name.value
        description = self.description.value
        self.descriptions_dict[name] = description
        self.tree.reset_icon_style()
        # If no parent, update root
        if self.parent.value != '':
            parent = self.parent.value
            if name not in self.tree.get_node_names():
                if parent not in self.tree.get_node_names():
                    # Create the parent node in the root
                    self.tree.create_node(parent, self.root)
                    self.tree.change_icon_style(parent, 'warning')
                # Add the new node to its parent parent
                self.tree.create_node(self.name.value, parent=parent)
            self.tree.change_icon_style(name, 'warning')
        self.parent.options = self.tree.get_node_names()

    def get_new_name(self, node):
        if node.name == self.root:
            prename = 'Criteria'
        else:
            prename = node.name
        i = 0
        node_names = [n.name for n in node.nodes]
        while True:
            i += 1
            name = prename + str(i)
            if name not in node_names:
                return name

    def removeCriteria(self, b):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Removing Criteria')
        selectedNode = self.tree.ipytree_tree.selected_nodes[0]
        self.tree.remove_node(selectedNode.name)
        self.parent.options = self.tree.get_node_names()

    #  def on_text_change(self, change):
        #  #  print('on_text_change.change={}'.format(change))
        #  #  print(self.selected_ipytree_node)
        #  if change['name']=='_property_lock' and change['new'] != {}:
            #  if change['new']['value'] != self.selected_ipytree_node.name:
                #  #  self.tree.rename_treelib_node(self.selected_ipytree_node.name, change['new']['value'])
                #  self.tree.rename_node(self.selected_ipytree_node.name, change['new']['value'])

    def on_select_change(self, change):
        #  print('on_select_change.change={}'.format(change))
        for l in self.links:
            l.unlink()
        self.links.clear()
        if not len(change['new']):
            return
        self.selected_ipytree_node = change['new'][0]
        self.name.value = self.selected_ipytree_node.name
        #  self.links.append(widgets.link((change['new'][0], 'name'), (self.name, 'value')))
        if self.selected_ipytree_node.name is not self.root:
            self.parent.value = self.tree.treelib_tree.parent(self.name.value).identifier
        else:
            self.parent.value = ''
        self.description.value = self.descriptions_dict[self.selected_ipytree_node.name]
        

