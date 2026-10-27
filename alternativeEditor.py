#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/alternativeEditor.py
import ipywidgets as widgets
from .constants import arisdf, alternative_rating_options, tab_titles
from .alternativeSelector import AlternativeSelector
from .titleAndHelp import TitleAndHelp

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Tuesday Jul 09, 2024 20:40:43 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Thursday Dec 19, 2024 16:26:55 CET'

#    TODO: 
#           Add things to do here

TAB = 1
TAB_TITLE = tab_titles[TAB]

if arisdf is not None:
    alternative_list = arisdf['Acronym'].to_list()
else:
    alternative_list = None

class AlternativeEditor():
    """
    This class creates all the widgets needed for the edition of alternatives. A alternativeSelector object is created to edit the alternative considered. Alternatives can be selected from a predefined list using a dropdown menu, aditionally, if necessary the user can manually enter alternatives not included in the predefined list by checking the 'Enter manually' checkbox. More alternative to consider in the AHP can be added/remove using the 'Add Alternative' and 'Remove Alternative' buttons.
    :param alternative_list: list, list with the names of the possible alternatives. By default, it is all reactors included in the IDOM-ARIS sharepoint list.
    :param nalternatives: int, number of alternatives to consider in the AHP    
    """
    def __init__(self, logger, alternative_list=alternative_list, nalternatives=2):
        self.logger = logger
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Initializing')
        self.alternative_list = alternative_list
        self.nalternatives = nalternatives
        self.title = TitleAndHelp('Edit the list of alternatives', 'docs/help_alternativeEditor.html')
        self.alternatives = []
        for i in range(nalternatives):
            self.alternatives.append(
                    AlternativeSelector(number=i+1, alternative_list=self.alternative_list)
                    )
        self.vbox = widgets.VBox(
                [alternative.allWidgets for alternative in self.alternatives]
                )

        self.addButton=widgets.Button(
            description='Add Alternative',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Add Alternative',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='85%'),
            icon='plus-square' # (FontAwesome names without the `fa-` prefix)
        )
        self.removeButton=widgets.Button(
            description='Remove Alternative',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Remove Alternative',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='85%'),
            icon='minus-square' # (FontAwesome names without the `fa-` prefix)
        )
        self.radioButtons = widgets.RadioButtons(
                options=alternative_rating_options,
                description='Rate the alternatives by:',
                disabled=False
                )
        self.allWidgets = widgets.VBox([
                self.title.allWidgets,
                self.vbox,
                widgets.HBox([self.addButton, self.removeButton]),
                self.radioButtons
                ])

        self.addButton.on_click(self.add_alternative)
        self.removeButton.on_click(self.remove_alternative)

    def get_all_outputs(self):
        data = {
            tab_titles[1]: self.get_selected_alternatives()
                }
        self.logger.log('debug', f'alternativeEditor.get_all_outputs.data={data}')
        return data

    def set_all_values(self, data):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Setting all values')
        self.logger.log('debug', f'alternativeEditor.set_all_values.data={data}')
        self.alternatives = []
        for i, alternative in enumerate(data[tab_titles[1]][:-1]):
            # Alternative selector doesn't exists
            self.alternatives.append(
                    AlternativeSelector(number=i+1, alternative_list=self.alternative_list, selected_alternative=alternative)
                    )
        self.nalternatives = len(data[tab_titles[1]]) - 1
        self.radioButtons.value = data[tab_titles[1]][-1]
        self.vbox = widgets.VBox(
                [alternative.allWidgets for alternative in self.alternatives]
                )
        self.allWidgets.children = [
                self.title.allWidgets, 
                self.vbox,
                widgets.HBox([self.addButton, self.removeButton]),
                self.radioButtons
                ]

    def get_selected_alternatives(self):
        """
        return a list with the selected alternatives
        """
        #  out = [a.text.value for a in self.alternatives] + [self.radioButtons.value]
        out = [a.combobox.value for a in self.alternatives] + [self.radioButtons.value]
        return out

    def add_alternative(self, b):
        """
        On clicking the 'Add Alternative' button, the number of alternatives in the AHP is increased and a new alternativeSelector is displayed.
        """
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Adding Alternative')
        self.nalternatives += 1
        if self.alternative_list:
            selected_alternative = self.alternative_list[self.nalternatives]
        else:
            selected_alternative = None
        new_alternative = AlternativeSelector(number=self.nalternatives, alternative_list=self.alternative_list, selected_alternative=selected_alternative)
        self.alternatives += [new_alternative]
        self.vbox.children = list(self.vbox.children) + [new_alternative.allWidgets]

    def remove_alternative(self, b):
        """
        On clicking the 'Remove Alternative' button, the number of alternatives in the AHP is reduced and the last alternativeSelector is removed.
        """
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Removing Alternative')
        if self.vbox.children:
            self.nalternatives -= 1
            self.alternatives = self.alternatives[:-1]
            self.vbox.children = list(self.vbox.children)[:-1]
