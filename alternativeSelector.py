#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/alternativeSelector.py
import ipywidgets as widgets
from .constants import section_label_style, alternative_label_style, arisdf

if arisdf is not None:
    alternative_list = arisdf['Acronym'].to_list()
else:
    alternative_list = None

class AlternativeSelector():
    def __init__(self, number=1, alternative_list=alternative_list, selected_alternative=None):
        self.label = widgets.Label(
                value = "Alternative {}".format(number),
                style = alternative_label_style,
                layout=widgets.Layout(width='30%')
                )
        if alternative_list:
            options = alternative_list
        else:
            options = []
        if not selected_alternative:
            selected_alternative = ''
            
        self.combobox = widgets.Combobox(
                options = options,
                value=selected_alternative,
                disabled=False,
                layout=widgets.Layout(width='70%')
                )
        self.allWidgets = widgets.HBox([
            self.label, self.combobox
            ])

