#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/ratingScalesTab.py
from collections import OrderedDict
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from .titleAndHelp import TitleAndHelp
from .constants import default_alternatives, make_default_tree, loading_bar, tab_titles, accordion_titles

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Friday Sep 06, 2024 19:41:52 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Friday Sep 06, 2024 19:58:41 CEST'

#    TODO: 
#           Add things to do here

class RatingScalesTab():
    def __init__(self):
        self.tree = None
        self.alternatives = None
        self.title = TitleAndHelp('Define Rating Scale for each leaf in the critera tree', 'docs/help_ratingScalesTab.md')
        self.out = widgets.Output()
        self.leafSelector = widgets.Dropdown(
                #  options=self.get_level_options(),
                #  value='0',
                # rows=10,
                description='Leaf:',
                disabled=False
            )

        self.allWidgets = widgets.VBox([
                self.title.allWidgets,
                self.out,
                self.leafSelector
                #  self.exportButton,
            ])

    def update(self, leafs):
        with self.out:
            clear_output()
            display(loading_bar)
        self.leafSelector.options = leafs

