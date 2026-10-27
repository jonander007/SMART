#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/ratingScaleCreator.py
from collections import OrderedDict
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from .constants import tab_titles, default_rating_scale_items
from .utilities import get_loading_bar
from .titleAndHelp import TitleAndHelp
from .combinedTree import CombinedTree
from .ratingScaleEditor import RatingScaleEditor

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Friday Sep 06, 2024 20:15:10 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Wednesday Nov 13, 2024 16:14:26 CET'

#    TODO: 
#           Add things to do here

loading_bar = get_loading_bar()

class RatingScaleCreator():
    def __init__(self):
        self.title = TitleAndHelp('Create Rating Scales for each leaf in the hierarchy', 'docs/help_ratingScaleCreator.html')
        self.out = widgets.Output()
        self.criteriaSelector = widgets.Select(
                #  options=self.criteriaOptions,
                #  value=None,
                # rows=10,
                description='Criteria:',
                disabled=False
            )

        self.ratingScales = OrderedDict()
        self.allWidgets = widgets.VBox([
            self.title.allWidgets,
            widgets.HBox([
                self.criteriaSelector,
                self.out,
                ])
            ])


    def update(self, tree_dict, silent=False):
        if not silent:
            with self.out:
                clear_output()
                display(loading_bar)
        self.tree = CombinedTree()
        self.tree.from_dict(tree_dict)
        self.criteriaOptions = [n.identifier for n in self.tree.treelib_tree.leaves()]
        # Remov scales for criteria that have been removed
        self.ratingScales = {key:self.ratingScales[key] for key in self.criteriaOptions if key in self.ratingScales}
        for criterion in self.criteriaOptions:
            if criterion not in self.ratingScales.keys():
                # Add Scale for new criteria
                self.ratingScales[criterion] = RatingScaleEditor()
            else:
                pass
        self.selectedScale = self.ratingScales[self.criteriaOptions[0]]
        # Unlink actions to functions
        self.criteriaSelector.unobserve(self.on_criteria_change)
        # Update questionaire selectors
        self.criteriaSelector.options = self.criteriaOptions
        self.criteriaSelector.value = self.criteriaOptions[0]
        # Link actions to functions again
        self.criteriaSelector.observe(self.on_criteria_change)
        # Display selected rating scale
        if not silent:
            with self.out:
                clear_output()
                display(self.selectedScale.allWidgets)

    def on_criteria_change(self, change):
        if change['type'] == 'change':
            self.selectedScale = self.ratingScales[self.criteriaSelector.value]
            with self.out:
                clear_output()
                display(self.selectedScale.allWidgets)

    def get_rating_scales(self):
        data = OrderedDict()
        for criterion, scaleEditor in self.ratingScales.items():
            data[criterion] = scaleEditor.get_all_outputs()
        #  print('ratingScaleCreator.get_rating_scales.data={}'.format(data))
        return data

    def get_all_outputs(self):
        return self.get_rating_scales()

    def set_all_values(self, data):
        for criterion, values in data.items():
            self.ratingScales[criterion] = RatingScaleEditor()
            self.ratingScales[criterion].set_all_values(values)

