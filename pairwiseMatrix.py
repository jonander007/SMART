#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/pairwiseMatrix.py
import numpy as np
import pandas as pd
import itertools
from ordered_set import OrderedSet
import ipywidgets as widgets
from IPython.display import clear_output
from .constants import default_criteria, border

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Monday Jul 08, 2024 16:22:23 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Wednesday Nov 20, 2024 19:16:37 CET'

#    TODO: 
#           Add things to do here

class PairwiseMatrix():
    def __init__(self, parent, criteria_list=default_criteria['empty']):
        self.parent = parent
        self.criteria_list = criteria_list

        self.inputs_widgets = {}
        self.output = widgets.Output()
        self.allWidgets = widgets.VBox([])
        self.bottomWidgets = widgets.VBox([])
        #  self.allWidgets.layout.border = border
        self.build_grid(self.parent)
        self.bottomWidgets.children = [self.grid]
        self.bottomWidgets.layout.border = border
        self.allWidgets.children = [self.label, self.bottomWidgets, self.output]
        with self.output:
            clear_output()
            print('Diagonal element must be 1')
            print('The value of upper triangular matrix should be reciporcal of corresponding lower tringular matrix ')

    def build_grid(self, parent, data=None):
        self.parent = parent
        self.label = widgets.HTML(value=f'Matrix for <b>{self.parent}</b>')
        if data:
            self.criteria_pairs = list(data.keys())
            string_set = OrderedSet()
            for pair in self.criteria_pairs:
                string_set.update(pair)
            self.criteria_list = list(string_set)
        else:
            self.criteria_pairs = [(a, b) for a,b in itertools.combinations(self.criteria_list, 2)]

        self.grid = widgets.GridspecLayout(
            len(self.criteria_list)+1, len(self.criteria_list)+1)
        for i in range(len(self.criteria_list)+1):
            for j in range(len(self.criteria_list)+1):
                if(i != j and (i == 0 or j == 0)):
                    if(i == 0):
                        labelindex = j-1
                    else:
                        labelindex = i-1

                    self.grid[i, j] = widgets.Label(
                        self.criteria_list[labelindex],

                    )

                if(i != 0 and j != 0):
                    self.grid[i, j] = self.create_Input(default=1,)

                    self.inputs_widgets['{}-{}'.format(i, j)] = self.grid[i, j]
                    self.grid[i, j].observe(self.on_cell_change, 'value')

                if(i == j and (i != 0 and j != 0)):
                    self.grid[i, j] = self.create_Input(default=1,)
                    self.inputs_widgets['{}-{}'.format(i, j)] = self.grid[i, j]
                    self.grid[i, j].observe(self.on_cell_change, 'value')
        self.bottomWidgets.children = [self.grid]
        self.allWidgets.children = [self.label, self.bottomWidgets, self.output]
        if data:
            self.set_values(data)

    def set_values(self, data):
        for criteria_pair, value in data.items():
            criteria_i, criteria_j = criteria_pair
            for i in range(1,len(self.criteria_list)+1):
                if self.grid[i, 0].value == criteria_i:
                    break
            for j in range(1,len(self.criteria_list)+1):
                if self.grid[0, j].value == criteria_j:
                    break
            self.inputs_widgets['{}-{}'.format(i, j)].value = value


    def create_Input(self, default=0):
        return widgets.Dropdown(
            options=[('1', 1), ('2', 2), ('3', 3), ('4', 4), ('5', 5), ('6', 6), ('7', 7), ('8', 8), ('9', 9),
                     ('1/2', 1/2), ('1/3', 1/3), ('1/4', 1/4), ('1/5', 1/5), ('1/6', 1/6), ('1/7', 1/7), ('1/8', 1/8), ('1/9', 1/9)],
            value=default,
            layout=widgets.Layout(width='50px',),
            disabled=False,
        )

    def on_cell_change(self, change):
        owner = change['owner']
        [row, column] = self.get_input_widget(owner).split('-')
        row = int(row)
        column = int(column)
        if(row != column and (row != 0 and column != 0)):
            self.grid[column, row].value = 1/change['new']
        if(row == column and (row != 0 and column != 0)):
            self.grid[column, row].value = 1

    def get_input_widget(self, owner):
        for key, value in self.inputs_widgets.items():
            if(value == owner):
                k = key
                break
        return k

    def values_to_np(self):
        length = len(self.criteria_list)
        mat = np.full((length, length), 1, dtype=float)
        for i in range(1, length+1):
            for j in range(1, length+1):
                mat[i-1, j-1] = self.grid[i, j].value
        return mat

    def to_df(self):
        values = self.values_to_np()
        df = pd.DataFrame(data=values, index=self.criteria_list, columns=self.criteria_list)
        return df
        
