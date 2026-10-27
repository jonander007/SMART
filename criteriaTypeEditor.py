#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/criteriaTypeEditor.py
import ipywidgets as widgets
import markdown
from IPython.display import display, HTML, Javascript
from .combinedTree import CombinedTree
from .constants import alternative_label_style, default_columns, tab_titles

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Monday Aug 05, 2024 15:24:07 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Friday Sep 06, 2024 12:03:27 CEST'

#    TODO: 
#           Add things to do here

class CriteriaTypeEditor():
    def __init__(self, criteria):
        self.label = widgets.Label(
                value = "Criteria: {}".format(criteria),
                style = alternative_label_style,
                layout=widgets.Layout(width='60%'),
                )
        self.typeDropDown = widgets.Dropdown(
                options = ['Quantitative', 'Qualitative'],
                value=None,
                disabled=False,
                layout=widgets.Layout(width='10%'),
                )
        self.scaleCheckBox = widgets.Checkbox(
                value=False,
                description='Create Rating Scale',
                disabled=False,
                indent=False,
                layout=widgets.Layout(width='10%'),
                )
        self.arisCheckBox = widgets.Checkbox(
                value=False,
                description='Get from ARIS',
                disabled=False,
                indent=False,
                layout=widgets.Layout(width='10%'),
                )
        self.arisDropDown = widgets.Dropdown(
                options = default_columns,
                value=None,
                disabled=True,
                layout=widgets.Layout(width='20%'),
                )
        self.arisCheckBox.observe(self.checkBoxChange, names='value')
        self.allWidgets = widgets.HBox([
            self.label, 
            self.scaleCheckBox,
            self.typeDropDown, 
            self.arisCheckBox, 
            self.arisDropDown
            ])

    def checkBoxChange(self, change):
        #  print(change)
        if change['new']:
            self.arisDropDown.disabled = not self.arisDropDown.disabled

    def to_dict(self):
        return {
                'Type': self.typeDropDown.value,
                'fromARIS': self.arisCheckBox.value,
                'ARIScolumn': self.arisDropDown.value,
                'RatingScale': self.scaleCheckBox.value
                }
