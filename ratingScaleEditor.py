#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/ratingScaleEditor.py
from collections import OrderedDict
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from .constants import tab_titles, default_rating_scale_items
from .utilities import get_loading_bar

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Friday Sep 06, 2024 20:54:36 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Wednesday Nov 13, 2024 16:15:10 CET'

#    TODO: 
#           Add things to do here

loading_bar = get_loading_bar()

class RatingScaleEditor():
    def __init__(self, items=default_rating_scale_items):
        self.items = items
        self.nitems = len(items)
        self.addButton=widgets.Button(
            description='Add Item',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Add Alternative',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='85%'),
            icon='plus-square' # (FontAwesome names without the `fa-` prefix)
        )
        self.removeButton=widgets.Button(
            description='Remove Item',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Remove Alternative',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='85%'),
            icon='minus-square' # (FontAwesome names without the `fa-` prefix)
        )
        self.checkBox = widgets.Checkbox(
                value=False,
                description='Quantitative',
                disabled=False,
                indent=False
                )

        self.textBoxes = [widgets.Text(value=item) for item in default_rating_scale_items]
        self.vbox = widgets.VBox(self.textBoxes)
        self.allWidgets = widgets.VBox([
            self.checkBox,
            self.vbox,
            widgets.HBox([
                self.addButton,
                self.removeButton
                ])
            ])
        self.addButton.on_click(self.add_item)
        self.removeButton.on_click(self.remove_item)
        self.checkBox.observe(self.checkBoxChange, names='value')
        
    def checkBoxChange(self, change):
        if change['new']: 
            # Changed to True
            for textBox in self.textBoxes:
                textBox.disabled = True
            self.addButton.disabled = True
            self.removeButton.disabled = True
        else:
            # Changed to False
            for textBox in self.textBoxes:
                textBox.disabled = False
            self.addButton.disabled = False
            self.removeButton.disabled = False

    def add_item(self, b):
        """
        On clicking the 'Add Alternative' button, the number of alternatives in the AHP is increased and a new alternativeSelector is displayed.
        """
        self.nitems += 1
        new_item = widgets.Text(placeholder='Enter item name')
        self.textBoxes += [new_item]
        self.vbox.children = list(self.vbox.children) + [new_item]

    def remove_item(self, b):
        """
        On clicking the 'Remove Alternative' button, the number of alternatives in the AHP is reduced and the last alternativeSelector is removed.
        """
        if self.vbox.children:
            self.nitems -= 1
            self.textBoxes = self.textBoxes[:-1]
            self.vbox.children = list(self.vbox.children)[:-1]

    def get_all_outputs(self):
        return [item.value for item in self.textBoxes] + [self.checkBox.value]

    def set_all_values(self, data):
        #print(data)
        self.textBoxes.clear()
        for item in data[:-1]:
            self.textBoxes.append(widgets.Text(value=item))
        # self.textBoxes = [widgets.Text(value=item) for item in data[:-1]]
        self.vbox.children = self.textBoxes
        self.checkBox.value = data[-1]
        if self.checkBox.value:
            for textBox in self.textBoxes:
                textBox.disabled = True
            self.addButton.disabled = True
            self.removeButton.disabled = True
        
