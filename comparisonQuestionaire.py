#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/comparisonQuestionaire.py
import ipywidgets as widgets
import itertools
from collections import OrderedDict
from ordered_set import OrderedSet
from .constants import default_criteria, saaty_scale, colors, border, togglebutton_colors

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Monday Jul 08, 2024 12:23:45 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Tuesday Nov 11, 2025 19:29:44 CET'

#    TODO: 
#           Add things to do here

class ComparisonQuestion():
    """
    ComparisonQuestion structure that handles the functionality of the widgets in a single question of the Saaty questionaires. 
    It displays a description title, tthe labels of each criterion and a ToggleButtons widget to compare the criteria pair.
    The description title changes depending on the button selected.
    """
    def __init__(self, criteria_pair, value=None, is_alternatives=False):
        """
        self.criteria_pair -tuple(str)- Tupla of names of the pair of criteria to compare
        self.description -str- Title of a comparison
        self.outpuLabel -ipywidgets.Label- Label handling the description format
        self.label0 -ipywidgets.Label- Label of the first criteria
        self.label1 -ipywidgets.Label- Label of the second criteria
        self.buttons -ipywidgets.ToggleButtons- TogggleButtons widget
        self.allWidgets -ipywidgets.VBox- VBox widget containing all widgets
        """
        self.criteria_pair = criteria_pair
        if not value:
            self.value = 1
        else:
            self.value = value
        self.is_alternatives = is_alternatives
        if self.is_alternatives:
            self.description = 'Alternative {} is {} Alternative {}'.format(criteria_pair[0], saaty_scale['1'], criteria_pair[1])
        else:
            self.description = 'Criterion {} is {} Criterion {}'.format(criteria_pair[0], saaty_scale['1'], criteria_pair[1])
        #  keys = ['1/{}'.format(i) for i in reversed(range(2,10))] + [str(i) for i in range(1,10)]
        #  values= [1/i for i in reversed(range(2, 10))] + [1] + [i for i in range(2,10)] 
        keys =  [str(i) for i in reversed(range(1,10))] + ['1/{}'.format(i) for i in range(2,10)]
        values= [i for i in reversed(range(1,10))] + [1/i for i in range(2, 10)]
        options = {key:value for key, value in zip(keys, values)}
        self.label0 = widgets.Label(value=self.criteria_pair[0],
                    style=dict(
                        font_weight='bold',
                        text_color='#dc2626'),
                    layout=widgets.Layout(width='150px',
                        white_space='normal'
                        )
                    )
        self.label1 = widgets.Label(value=self.criteria_pair[1],
                    style=dict(
                        font_weight='bold',
                        text_color='#1c9ce8'),
                    layout=widgets.Layout(width='150px',
                        white_space='normal'
                        )
                    )
        self.buttons = widgets.ToggleButtons(
                    options=options,
                    value=self.value,
                    disabled=False,
                    button_style='', # 'success', 'info', 'warning', 'danger' or ''
                    style=dict(
                        button_width='40px',
                        )
                ) 
        self.buttons.observe(self.on_select_change, 'value')
        self.outputLabel = widgets.Label(value=self.description,
                    style=dict(
                        font_weight='bold',
                        font_size='18px',
                        text_color=colors['1']
                        )
                    )
        self.allWidgets = widgets.VBox([
            self.outputLabel,
            widgets.HBox([self.label0, self.buttons, self.label1]),
            ])
        self.allWidgets.layout.border_left = border
        self.allWidgets.layout.border_right = border
        self.allWidgets.layout.border_top = border
        self.value = self.buttons.value

    def on_select_change(self, change):
        """Handle change in title and when a new button is selected"""
        #  print(change)
        if change['new']:
            if change['new'] < 1:
                if self.is_alternatives:
                    self.description = 'Alternative {} is {} as Alternative {}'.format(self.criteria_pair[1], saaty_scale[str(int(1/change['new']))], self.criteria_pair[0])
                else:
                    self.description = 'Criterion {} is {} as Criterion {}'.format(self.criteria_pair[1], saaty_scale[str(int(1/change['new']))], self.criteria_pair[0])

                saaty_key = str(int(-1/change['new']))
            elif change['new'] == 1:
                if self.is_alternatives:
                    self.description = 'Alternative {} is {} as Alternative {}'.format(self.criteria_pair[0], saaty_scale[str(int(change['new']))], self.criteria_pair[1])
                else:
                    self.description = 'Criterion {} is {} as Criterion {}'.format(self.criteria_pair[0], saaty_scale[str(int(change['new']))], self.criteria_pair[1])
                saaty_key=str(int(change['new']))
            else:
                if self.is_alternatives:
                    self.description = 'Alternative {} is {} as Alternative {}'.format(self.criteria_pair[0], saaty_scale[str(int(change['new']))], self.criteria_pair[1])
                else:
                    self.description = 'Criterion {} is {} as Criterion {}'.format(self.criteria_pair[0], saaty_scale[str(int(change['new']))], self.criteria_pair[1])
                saaty_key=str(int(change['new']))
            self.outputLabel.value = self.description
            self.outputLabel.style.text_color = colors[saaty_key]

        
class ComparisonQuestionaire():
    """
    ComparisonQuestionaire structure handling a questionaire consistin of the comparisons of all pairs of criteria in a list in the Saaty scale.
    """
    def __init__(self, parent, criteria_list=default_criteria['empty'], is_alternatives=False):
        """
        self.parrent -str- Name of the parent whose criteria are to compare.
        self.criteria_list -list(str)- List of criteria to compare
        self.questions -dict(ComparisonQuestion)- Dictionary with key the criteria pair and value the ComparisonQuestion object
        self.criteria_pairs -list(tuple(str))- List of unique criteria pairs.
        self.widget_list -list- List of VBoxes for each ComparreQuestion
        self.allWidgets -ipywidgets.VBox- VBox widget containing all widgets

        """
        self.parent = parent
        self.criteria_list = criteria_list
        self.is_alternatives = is_alternatives
        self.questions = OrderedDict()
        self.allWidgets = widgets.VBox([])
        self.build_questionaire(self.parent)

    def build_questionaire(self, parent, data=None):
        self.parent = parent
        self.label = widgets.HTML(value=f'Comparisons for <b>{self.parent}</b>')
        self.widget_list = []
        if data:
            self.criteria_pairs = list(data.keys())
            string_set = OrderedSet()
            for pair in self.criteria_pairs:
                string_set.update(pair)
            self.criteria_list = list(string_set)
        else:
            self.criteria_pairs = [(a, b) for a,b in itertools.combinations(self.criteria_list, 2)]
        self.questions = OrderedDict()
        for criteria_pair in self.criteria_pairs:
            self.questions[criteria_pair] = ComparisonQuestion(criteria_pair, is_alternatives=self.is_alternatives)
            self.widget_list.append(self.questions[criteria_pair].allWidgets)
        self.allWidgets.children = [self.label] + self.widget_list
        self.allWidgets.layout.border_bottom = border
        if data:
            for key, item in data.items():
                self.questions[key].buttons.value = item


    def comparisons_to_dict(self):
        comparisons = OrderedDict()
        for key, item in self.questions.items():
            comparisons[key] = item.buttons.value
        return comparisons

    def comparisons_from_dict(self, parent, data):
        self.parent = parent
        self.build_questionaire(self.parent, data)

