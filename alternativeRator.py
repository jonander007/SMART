#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/alternativeRator.py
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from .titleAndHelp import TitleAndHelp
from .constants import alternative_rating_options, tab_titles
from .utilities import get_loading_bar, validate_inputs
from .notificationBar import NotificationBar
from .alternativeComparator import AlternativeComparator
from .alternativeRating import AlternativeRating

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Thursday Sep 05, 2024 11:27:06 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Thursday Dec 19, 2024 18:47:18 CET'

#    TODO: 
#           Add things to do here

TAB = 4
TAB_TITLE = tab_titles[TAB]

loading_bar = get_loading_bar()

class AlternativeRator():
    def __init__(self, logger):
        self.logger = logger
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Initializing')
        self.out = widgets.Output()
        self.notif = NotificationBar()
        self.allWidgets = widgets.VBox([self.notif.widget, self.out])
        self.alternativeComparator = None
        self.alternativeRating = None
        self.radio_value = None
        self.rator = None
        self.invalid = False

    def update(self, radio_value, tree_dict, alternatives):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Updating')
        with self.out:
            clear_output()
            display(loading_bar)
        self.invalid = validate_inputs(self.notif, tree_dict, None, alternatives, None)
        if not self.invalid:
            if self.radio_value == radio_value:
                self.rator.update(tree_dict, alternatives)
            else:
                self.radio_value = radio_value
                if radio_value == alternative_rating_options[0]:
                    if self.alternativeComparator:
                        self.alternativeComparator.update(tree_dict, alternatives)
                    else:
                        self.alternativeComparator = AlternativeComparator()
                    self.rator = self.alternativeComparator
                else:
                    if self.alternativeRating:
                        self.alternativeRating.update(tree_dict, alternatives)
                    else:
                        self.alternativeRating = AlternativeRating()
                    self.rator = self.alternativeRating
                self.rator.update(tree_dict, alternatives)
            with self.out:
                clear_output()
                display(self.rator.allWidgets)

    def render(self):
        """Display the current rator's widgets into the output area.

        Used by deferred loading: set_all_values() builds + fills the rator with
        silent=True (no render), then this performs the single final render.
        """
        if self.rator:
            with self.out:
                clear_output()
                display(self.rator.allWidgets)
            # If the rator is a rating-scale editor, render + open its rating
            # table so the populated values are visible immediately.
            if isinstance(self.rator, AlternativeRating):
                if hasattr(self.rator, 'render_table'):
                    self.rator.render_table()

    def get_all_outputs(self):
        if self.rator:
            if self.radio_value == alternative_rating_options[0]:
                data = self.rator.comparisons_to_dict()
            else:
                data = self.rator.get_all_outputs()
        else:
            data = {}
        return data

    def set_all_values(self, data):
        alternatives = data[tab_titles[1]][tab_titles[1]][:-1]
        tree_dict    = data[tab_titles[2]][tab_titles[2]]
        radio_value  = data[tab_titles[1]][tab_titles[1]][-1]

        if radio_value == alternative_rating_options[0]:
            if not self.alternativeComparator:
                self.alternativeComparator = AlternativeComparator()
            self.rator = self.alternativeComparator
        else:
            if not self.alternativeRating:
                self.alternativeRating = AlternativeRating()
            self.rator = self.alternativeRating

        # update() must run first so all sub-widgets (selectors, rating tables)
        # are created before set_all_values tries to fill them with data.
        # AlternativeRating renders its rating table in set_all_values, so pass
        # silent=True here to avoid a double-render (→ IndexError pop from empty list).
        if isinstance(self.rator, AlternativeRating):
            self.rator.update(tree_dict, alternatives, silent=True)
        else:
            self.rator.update(tree_dict, alternatives)

        if tab_titles[4] in data.keys():
            self.rator.set_all_values(data[tab_titles[4]])

    def get_compare_objects(self):
        return self.rator.get_compare_objects()
            

