#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/criteriaEditor.py
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import numpy as np
import time
import itertools
import os
import plotly.graph_objects as go
from collections import OrderedDict
from ordered_set import OrderedSet
import pandas as pd
from .ahp import Compare
from .constants import default_criteria, default_goals, yellow, transparent, text_fontdict, tmp_dir, write_html_config
from .utilities import build_label_text, make_pie_fig
from .combinedTree import CombinedTree
from .pairwiseMatrix import PairwiseMatrix
from .comparisonQuestionaire import ComparisonQuestionaire


__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Tuesday Jul 02, 2024 16:28:22 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Friday Nov 07, 2025 09:07:49 CET'

#    TODO: 
#           Add things to do here


class QuestionaireAndMatrix():
    def __init__(self, criteria_list=default_criteria['empty'], parent=default_goals['empty'], precision=5, is_alternatives=False, colors=None):
        self.criteria_list = criteria_list
        self.parent = parent
        self.precision = precision
        self.is_alternatives = is_alternatives
        self.criteria_colors = colors
        self.comparisonQuestionaire = ComparisonQuestionaire(self.parent, self.criteria_list, is_alternatives=self.is_alternatives)
        self.pairwiseMatrix = PairwiseMatrix(self.parent, self.criteria_list)
        self.ahp_compare = Compare(self.parent, self.comparisonQuestionaire.comparisons_to_dict(), precision=self.precision)
        self.outputLabel = widgets.HTML(
                value = build_label_text(self.ahp_compare.consistency_ratio),
                layout=widgets.Layout(margin='4px 0 8px 0'),
                )
		
        #  self.fig = make_pie_fig_old(
                #  labels=list(self.ahp_compare.local_weights.keys()),
                #  values=list(self.ahp_compare.local_weights.values()))
        df = pd.DataFrame(columns=['Criteria', 'Weight'])
        for criteria, weight in self.ahp_compare.local_weights.items():
            df = pd.concat([pd.DataFrame([[criteria, weight]], columns=df.columns), df if not df.empty else None], ignore_index=True)
        if isinstance(self.criteria_colors, pd.DataFrame):
            self.fig = make_pie_fig(df, self.criteria_colors, title=parent, center_text=self.ahp_compare.consistency_ratio)
        else:
            self.fig = make_pie_fig(df, title=parent, center_text=self.ahp_compare.consistency_ratio)
        self.plot = go.FigureWidget(self.fig)
        self.out = widgets.Output()

        self.tabs = widgets.Tab([
                self.comparisonQuestionaire.allWidgets,
                self.pairwiseMatrix.allWidgets], 
                titles=['Questionaire', 'Matrix'])

        self.allWidgets = widgets.VBox([])
        children = [
            self.tabs,
            self.outputLabel,
            self.out,
        ]
        self.allWidgets.children = children

        self.make_links()

    def make_links(self):
        dropdowns = {}
        triu = np.triu_indices(n=len(self.criteria_list), m=len(self.criteria_list), k=1)
        for i, j in zip(triu[0], triu[1]):
            dropdowns[(self.criteria_list[i], self.criteria_list[j])] = self.pairwiseMatrix.inputs_widgets['{}-{}'.format(i+1, j+1)]
        
        for key, button in self.comparisonQuestionaire.questions.items():
            self.link_widgets(button.buttons, dropdowns[key])

    #  def update(self, parent, criteria_list):
        #  #  self.remove_links()
        #  self.parent = parent
        #  self.criteria_list = criteria_list
        #  criteria_pairs = [(a, b) for a,b in itertools.combinations(self.criteria_list, 2)]
        #  data = OrderedDict()
        #  for pair in criteria_pairs:
            #  if pair in self.comparisonQuestionaire.criteria_pairs:
                #  data[pair] = self.comparisonQuestionaire.questions[pair].buttons.value
            #  else:
                #  data[pair] = 1
        #  self.comparisonQuestionaire.build_questionaire(self.parent, data)
        #  self.pairwiseMatrix.build_grid(self.parent, data)
        #  self.make_links()
        #  self.update_ahp()
        #  self.update_label()
        #  self.update_plot()

    def export(self, df_format='csv', im_format='png'):
        # Save the comparison matrix
        df = self.pairwiseMatrix.to_df()
        df_file = '{}_{}.{}'.format(self.parent.replace(' ','_'), self.ahp_compare.consistency_ratio, df_format)
        df_file = os.path.join(tmp_dir, df_file)
        if df_format == 'csv':
            df.to_csv(df_file, float_format='{:.3f}')
        else:
            df.to_html(df_file, float_format='%.3f')
        # Save plot
        im_file = '{}_CR{}.{}'.format(self.parent.replace(' ', '_'), self.ahp_compare.consistency_ratio, im_format)
        im_file = os.path.join(tmp_dir, im_file)
        #  if im_format == 'png':
        if im_format == 'html':
            self.fig.write_html(im_file, full_html=False, config=write_html_config)
        else:
            self.fig.write_image(im_file)
        return df_file, im_file

    def comparisons_to_dict(self):
        return self.comparisonQuestionaire.comparisons_to_dict()

    def comparisons_from_dict(self, parent, data, colors=None):
        self.parent = parent
        self.criteria_colors = colors
        self.update_criteria_list(data)
        self.comparisonQuestionaire.comparisons_from_dict(self.parent, data)
        self.pairwiseMatrix.build_grid(self.parent, data)
        self.update_ahp()
        self.update_label()
        self.update_plot(parent)
        self.make_links()

    def update_criteria_list(self, data):
        criteria_pairs = list(data.keys())
        string_set = OrderedSet()
        for pair in criteria_pairs:
            string_set.update(pair)
        self.criteria_list = list(string_set)
        

    def update_label(self):
        self.outputLabel.value = build_label_text(self.ahp_compare.consistency_ratio)
        if self.ahp_compare.consistency_ratio > 0.1:  # noqa — kept for legacy callers
            self.allWidgets.add_class('custom-bg')
        else:
            self.allWidgets.remove_class('custom-bg')

    def update_plot(self, title=None):
        data_df = pd.DataFrame(self.ahp_compare.local_weights, index=[0]).transpose()
        data_df = data_df.reset_index()
        data_df = data_df.rename(columns={'index':'Criteria'})
        data_df.columns = ['Weight' if isinstance(col, (int, float)) else col for col in data_df.columns]
        self.fig.data[0].values = data_df['Weight']
        self.fig.data[0].labels = data_df['Criteria']
        #  self.fig.data[0].values = list(self.ahp_compare.local_weights.values())
        #  self.fig.data[0].labels=list(self.ahp_compare.local_weights.keys())
        if isinstance(self.criteria_colors, pd.DataFrame):
            data_df = data_df.merge(self.criteria_colors[['Criteria', 'Color', 'Color Plotly', 'Hatches']], on='Criteria', how='left')
            colors = data_df['Color Plotly'].to_list()
            hatches = data_df['Hatches'].to_list()
            #  print(hatches)
            maxlen = max(len(s) for s in hatches)
            sizes = [16/len(s) for s in hatches if len(s) > 0]
            hatches = [s[0] for s in hatches if len(s) > 0]
            self.fig.update_traces(
                    title='{:.2f}'.format(self.ahp_compare.consistency_ratio),
                    marker=dict(
                        colors=colors, 
                        pattern=dict(shape=hatches, fillmode='overlay', size=sizes),
                        line=dict(color='DarkSlateGrey')
                        )
                    )
        else:
            self.fig.update_traces()
        if title:
            self.fig.update_layout(
                title=dict(
                    text=title,
                    #  tickfont=dict(size=16),
                    font=text_fontdict,
                    #  categoryorder='array',
                    #  categoryarray=alternatives
                    x=0.5
                    ),
                )
        with self.out:
            clear_output()
            display(self.fig)

    def update_ahp(self):
        self.ahp_compare = Compare(self.parent, self.comparisonQuestionaire.comparisons_to_dict(), precision=self.precision)

    def link_widgets(self, button, dropdown):
        def on_button_change(change):
            dropdown.value = change['new']
            self.update_ahp()
            self.update_label()
            self.update_plot()
        def on_dropdown_change(change):
            button.value = change['new']
            self.update_ahp()
            self.update_label()
            self.update_plot()
        button.observe(on_button_change, names='value')
        dropdown.observe(on_dropdown_change, names='value')

    def get_criteria_options(self, level=0):
        out = []
        if level == 0:
            out.append(self.tree.ipytree_root.name)
        else:
            candidates = self.tree.get_node_names(level=level)
            for criteria in candidates:
                if len(self.tree.treelib_tree.children(criteria)) > 1:
                    out.append(criteria)
        return out

    def get_level_options(self):
        levels = []
        for level in range(self.tree.treelib_tree.depth()):
            for nodename in self.tree.get_node_names(level=level):
                if len(self.tree.treelib_tree.children(nodename)) > 1:
                    levels.append(str(level))
                    break
        return levels




