#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/alternativeRating.py
from collections import OrderedDict
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from .titleAndHelp import TitleAndHelp
from .ahp import Compare
from .constants import tab_titles, accordion_titles
from .utilities import get_loading_bar
from .questionaireAndMatrix import QuestionaireAndMatrix
from .combinedTree import CombinedTree
from .ratingTable import RatingTable
from .ratingTablesEditor import RatingTablesEditor
from .ratingScaleCreator import RatingScaleCreator
from .ratingScaleComparator import RatingScaleComparator

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Thursday Sep 05, 2024 10:19:26 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Wednesday Nov 13, 2024 16:11:15 CET'

#    TODO: 

loading_bar = get_loading_bar()

class AlternativeRating():
    def __init__(self):
        self.tree = None
        self.alternatives = None
        self.title = TitleAndHelp('Define Rating Scale and create the Rating Tables', 'docs/help_alternativeRating.html')
        self.out = widgets.Output()
        self.exportButton = widgets.Button(
            description='Export Ratings to CSV',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Export Ratings to CSV',
            style={'description_width': 'initial'},
            )

        self.ratingScaleCreator = RatingScaleCreator()
        self.ratingScaleComparator = RatingScaleComparator()
        self.ratingTablesEditor = RatingTablesEditor()
        self.rating_options = None
        self.ratingTables = OrderedDict()
        self.tree_dict = None      # set by update(); set_all_values() reads it
        self._last_rt_scales = None
        self._last_rt_alts = None

        self.accordion = widgets.Accordion(titles=accordion_titles, 
                children=[
                    self.ratingScaleCreator.allWidgets,
                    self.ratingScaleComparator.allWidgets,
                    self.ratingTablesEditor.allWidgets
                    ])
        self.allWidgets = widgets.VBox([
                self.title.allWidgets,
                self.accordion,
                #  self.exportButton,
            ])
        self.accordion.observe(self.tab_change, names='selected_index')

    def tab_change(self, change):
        if change['new'] is not None:
            if accordion_titles[change['new']] == accordion_titles[1]:
                self.ratingScaleComparator.update(self.tree_dict, self.ratingScaleCreator.get_rating_scales())
            elif accordion_titles[change['new']] == accordion_titles[2]:
                # If the table already has loaded data pending render, show it.
                if getattr(self.ratingTablesEditor, '_dirty', False):
                    self.ratingTablesEditor.render_if_needed()
                else:
                    current_scales = self.ratingScaleCreator.get_rating_scales()
                    if (current_scales != self._last_rt_scales
                            or self.alternatives != self._last_rt_alts):
                        self._last_rt_scales = current_scales
                        self._last_rt_alts = self.alternatives
                        self.ratingTablesEditor.update(current_scales, self.alternatives)

        #  print(accordion_titles[change['new']])


    def update(self, tree_dict, alternatives, silent=False):
        self.tree_dict = tree_dict
        self.alternatives = alternatives
        # silent=True (used during case loading): no sub-component renders here.
        # Rendering during load enters Output context managers multiple times in a
        # single nbclient cell, unbalancing the output_hook_stack → IndexError.
        # The tab renders normally later when the user navigates to it (tab_change).
        self.ratingScaleCreator.update(tree_dict, silent=silent)
        self.ratingScaleComparator.update(tree_dict, self.ratingScaleCreator.get_rating_scales(), silent=silent)
        self.ratingTablesEditor.update(self.ratingScaleCreator.get_rating_scales(), alternatives, silent=silent)

    def get_all_outputs(self):
        data = OrderedDict()
        data[accordion_titles[0]] = self.ratingScaleCreator.get_rating_scales()
        data[accordion_titles[1]] = self.ratingScaleComparator.get_all_outputs()
        data[accordion_titles[2]] = self.ratingTablesEditor.get_all_outputs()
        return data

    #  def ratings_from_dict(self, data, tree_dict):
        #  self.update(tree_dict, data[tab_titles[4]].keys())
        #  self.set_all_values(data[tab_titles[4]])

    def set_all_values(self, data):
        # 1. Restore rating scale definitions first
        if accordion_titles[0] in data.keys():
            self.ratingScaleCreator.set_all_values(data[accordion_titles[0]])
        restored_scales = self.ratingScaleCreator.get_rating_scales()
        # 2. Restore pairwise comparisons between scale items.
        #    update() ran BEFORE this method, when ratingScaleCreator still held
        #    the DEFAULT scales (High/Medium/Low) — so the comparison
        #    questionaires were built around those defaults. Rebuild them from
        #    the now-restored scales before applying the saved values, exactly
        #    as step 3 below does for the rating table. Without this the default
        #    pairs survive, get_all_outputs() returns them, and the autosave
        #    writes them straight back: the .smt stays corrupt forever and the
        #    exported questionnaire asks the expert to compare "High vs Medium"
        #    instead of the real scale options.
        if accordion_titles[1] in data.keys() and self.tree_dict is not None:
            self.ratingScaleComparator.update(
                self.tree_dict, restored_scales, silent=True
            )
            self.ratingScaleComparator.set_all_values(data[accordion_titles[1]])
        # 3. Rebuild RatingTable widgets with the CORRECT scale options (not defaults),
        #    then fill in the saved values. Render is deferred (set_all_values marks
        #    the table _dirty); render_table() below performs the single render.
        if accordion_titles[0] in data.keys() and accordion_titles[2] in data.keys():
            # silent=True: recreate selectors with correct options but don't render yet
            self.ratingTablesEditor.update(
                restored_scales, self.alternatives, silent=True
            )
            self.ratingTablesEditor.set_all_values(
                data[accordion_titles[2]], restored_scales
            )
            # Remember rendered state so tab_change doesn't rebuild unnecessarily
            self._last_rt_scales = restored_scales
            self._last_rt_alts = self.alternatives

    def render_table(self):
        """Force the rating table to render and open its accordion section.

        Called by deferred loading so the populated table is visible immediately
        without the user having to click the 'Rating Table' accordion header.
        """
        if getattr(self.ratingTablesEditor, '_dirty', False):
            self.ratingTablesEditor.render_if_needed()
        # Open the Rating Table section (index 2) so the table is visible
        try:
            self.accordion.selected_index = 2
        except Exception:
            pass

    def get_compare_objects(self):
        out = {}
        rating_tables = self.ratingTablesEditor.get_all_outputs()
        rating_scales = self.ratingScaleCreator.get_rating_scales()
        rating_compares = self.ratingScaleComparator.get_compare_objects()
        renormalized_weights = self.renormalize_rating_scales(rating_compares)
        for subcriterion, scale in rating_scales.items():
            subcriterion_data = {}
            if scale[-1]:
                for alternative in rating_tables.keys():
                    subcriterion_data[alternative] = rating_tables[alternative][subcriterion]
            else:
                for alternative in rating_tables.keys():
                    #  subcriterion_data[alternative] = rating_compares[subcriterion].local_weights[rating_tables[alternative][subcriterion]]
                    subcriterion_data[alternative] = renormalized_weights[subcriterion][rating_tables[alternative][subcriterion]]
            out[subcriterion] = Compare(subcriterion, subcriterion_data, is_rating=True)
        return out
        
    def renormalize_rating_scales(self, rating_compares):
        renormalized_weights = {}
        for subcriterion in rating_compares.keys():
            max_val = max(rating_compares[subcriterion].local_weights.values())
            renormalized_weights[subcriterion] = {k:v/max_val for k,v in rating_compares[subcriterion].local_weights.items()}
        #  print(f'alternativeRating.renormalize_rating_scales.renormalized_weights={renormalized_weights}')
        return renormalized_weights
            
