#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/ratingTablesTab.py
from collections import OrderedDict
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from .titleAndHelp import TitleAndHelp
from .constants import default_alternatives, make_default_tree, loading_bar, tab_titles

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Friday Sep 06, 2024 19:32:17 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Friday Sep 06, 2024 19:40:53 CEST'

#    TODO: 
#           Add things to do here

class RatingTablesTab():
    def __init__(self):
        self.rating_scales = None
        self.alternatives = None
        self.title = TitleAndHelp('Rate the alternatives assigning a value in the Rating Scale for each subcriteria', 'docs/help_ratingTablesTab.md')
        self.out = widgets.Output()
        self.exportButton = widgets.Button(
            description='Export Ratings to CSV',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Export Ratings to CSV',
            style={'description_width': 'initial'},
            )

        self.ratingTables = OrderedDict()
        self.rating_options = None
        self.allWidgets = widgets.VBox([
                self.title.allWidgets,
                self.out,
                self.exportButton,
            ])

    def update(self, rating_scales, alternatives):
        with self.out:
            clear_output()
            display(loading_bar)
        # Update tree object
        self.tree = CombinedTree()
        self.tree.from_dict(tree_dict)
        self.alternatives = alternatives
        # Get list of leaves in the tree
        self.subcriteria = self.tree.get_node_names(level)
        # Remove rating tables that have been removed
        self.ratingTables = OrderedDict({key:self.ratingTables[key] for key in self.alternatives if key in self.ratingTables})
        if self.rating_options:
            for alternative in self.alternatives:
                if alternative in self.ratingTables.keys():
                    # If the alternative is alredy existing, update the options if they are new
                    new_rating_options = {subcriterion:[node.identifier for node in self.tree.treelib_tree.children(subcriterion)] for subcriterion in self.subcriteria}
                    if self.rating_options != new_rating_options:
                        self.rating_options = new_rating_options
                    self.ratingTables[alternative].update(self.rating_options)
                else:
                    # Alternative is new, create a new rating table
                    self.ratingTables[alternative] = RatingTable(alternative, self.rating_options)
        else:
            # First time update is called populate the rating tables
            self.rating_options = {subcriterion:[node.identifier for node in self.tree.treelib_tree.children(subcriterion)] for subcriterion in self.subcriteria}
            for alternative in self.alternatives:
                self.ratingTables[alternative] = RatingTable(alternative, self.rating_options)

        self.vbox = widgets.VBox([ratingTable.allWidgets for ratingTable in self.ratingTables.values()])
        with self.out:
            clear_output()
            display(self.vbox)
