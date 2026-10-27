#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/criteriaSelector.py
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from .combinedTree import CombinedTree
from .constants import loading_bar, section_label_style
from .criteriaTypeEditor import CriteriaTypeEditor
from .titleAndHelp import TitleAndHelp

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Monday Aug 05, 2024 15:17:40 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Monday Aug 12, 2024 20:32:03 CEST'

#    TODO: 
#           Add things to do here

class CriteriaTypeSelector():
    def __init__(self, tree=None):
        self.criteria = []
        #  if tree:
            #  self.criteria = [n.identifier for n in tree.treelib_tree.leaves()]
        #  else:
            #  self.criteria = [n.identifier for n in make_default_tree['empty'].treelib_tree.leaves()]
        
        self.title = TitleAndHelp('Select the type of each subcriteria', 'docs/help_criteriaTypeSelector.md')
        self.out = widgets.Output()


        self.vbox = widgets.VBox([])

        self.allWidgets = widgets.VBox([
                self.title.allWidgets,
                self.vbox,
                self.out
            ])

    def update(self, tree_dict):
        with self.out:
            clear_output()
            display(loading_bar)
        # Update tree object
        self.tree = CombinedTree()
        self.tree.from_dict(tree_dict)
        self.criteria = [n.identifier for n in self.tree.treelib_tree.leaves()]
        self.selectors = {}
        for criterion in self.criteria:
            self.selectors[criterion] = CriteriaTypeEditor(criterion)
        self.vbox.children = [selector.allWidgets for selector in self.selectors.values()]
        with self.out:
            clear_output()

    def get_all_outputs(self):
        data = {
                'CriteriaType': self.to_dict()
                }
        return data

    def to_dict(self):
        mydict = {}
        for criterion in self.criteria:
            mydict[criterion] = self.selectors[criterion].to_dict()
        return mydict

