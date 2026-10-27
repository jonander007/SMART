#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/criteriaComparator.py
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from IPython.display import FileLink
from base64 import b64encode
import os
import itertools
from collections import OrderedDict
from .constants import tab_titles, tmp_dir
from .utilities import get_loading_bar
from .questionaireAndMatrix import QuestionaireAndMatrix
from .combinedTree import CombinedTree
from .titleAndHelp import TitleAndHelp
from .utilities import create_zip
from .ahp import Compare

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Tuesday Jul 09, 2024 15:55:36 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Tuesday Jul 15, 2025 18:55:24 CEST'

#    TODO: 
#           Add things to do here

TAB = 3
TAB_TITLE = tab_titles[TAB]

loading_bar = get_loading_bar()

class CriteriaComparator():
    def __init__(self, logger):
        self.logger = logger
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Initializing')
        self.tree = None
        self.criteria_colors = None
        self.title = TitleAndHelp('Perform the pairwise comparison of the criteria/subcriteria', 'docs/help_criteriaComparator.html')
        self.out = widgets.Output()
        self.downloadOut = widgets.Output()
        self.levelSelector = widgets.Dropdown(
                #  options=self.get_level_options(),
                #  value='0',
                # rows=10,
                description='Level:',
                disabled=False
            )
        self.criteriaSelector = widgets.Select(
                #  options=self.get_criteria_options(level=0),
                #  value=None,
                # rows=10,
                description='Criteria:',
                disabled=False
            )
        self.exportButton = widgets.Button(
            description='Export Matrices and Figures',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Export Matrices and Figures',
            style={'description_width': 'initial'},
        )

        self.allWidgets = widgets.VBox([
                self.title.allWidgets,
                widgets.HBox([self.levelSelector, self.criteriaSelector]),
                self.out,
                self.exportButton,
                self.downloadOut
            ])
        self.allQuestionaires = {}
        self.exportButton.on_click(self.export_matrices_and_figures)

    def build_new_questionaire(self, children):
        criteria_pairs = [(a, b) for a, b in itertools.combinations(children, 2)]
        questions = OrderedDict((key, 1) for key in criteria_pairs)
        return questions

    def update_existing_questionaire(self, criterion, children):
        criteria_pairs = [(a, b) for a, b in itertools.combinations(children, 2)]
        questions = OrderedDict()
        for pair in criteria_pairs:
            if pair in self.allQuestionaires[criterion]:
                questions[pair] = self.allQuestionaires[criterion][pair]
            else:
                questions[pair] = 1
        return questions


    def update(self, tree_dict, criteria_colors=None, render=True):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Updating')
        self.criteria_colors = criteria_colors
        #  print(tree_dict)
        if render:
            with self.out:
                clear_output()
                display(loading_bar)
        # Update tree object
        self.tree = CombinedTree()
        self.tree.from_dict(tree_dict)
        level_options = self.get_level_options()
        criteria_options = self.get_criteria_options(level=0)
        self.criteria_to_compare = self.get_criteria_to_compare()
        # Remove questionaires for criteria that have been removed
        self.allQuestionaires = {key:self.allQuestionaires[key] for key in self.criteria_to_compare if key in self.allQuestionaires}
        for criterion in self.criteria_to_compare:
            children = [node.identifier for node in self.tree.treelib_tree.children(criterion)]
            if criterion not in self.allQuestionaires.keys():
            # Add questionaires for new criteria
                #  self.allQuestionaires[criterion] = QuestionaireAndMatrix(criteria_list=children, parent=criterion)
                self.allQuestionaires[criterion] = self.build_new_questionaire(children)
            else:
            # Update questionaires for already existing criteria
                #  self.allQuestionaires[criterion].update(children)
                self.allQuestionaires[criterion] = self.update_existing_questionaire(criterion, children)
        self.selectedQuestionaire = QuestionaireAndMatrix()
        if len(self.tree.treelib_tree.children(self.tree.root)) > 1:
        # Root has more than one criteria
            #  self.selectedQuestionaire = self.allQuestionaires[self.tree.root]
            self.selectedQuestionaire.comparisons_from_dict(
                    self.tree.root,
                    self.allQuestionaires[self.tree.root],
                    self.criteria_colors)
        else:
        # Root has only one criteria
            criteria = next(iter(self.allQuestionaires))
            #  self.selectedQuestionaire = self.allQuestionaires[criteria]
            self.selectedQuestionaire.comparisons_from_dict(criteria, self.allQuestionaires[criteria], self.criteria_colors)
        # Unlink actions to functions
        self.levelSelector.unobserve(self.on_level_change)
        self.criteriaSelector.unobserve(self.on_criteria_change)
        # Update questionaire selectors
        self.levelSelector.options = level_options
        self.levelSelector.value = level_options[0]
        self.criteriaSelector.options = criteria_options
        self.criteriaSelector.value = criteria_options[0]
        # Link actions to functions again
        self.levelSelector.observe(self.on_level_change)
        self.criteriaSelector.observe(self.on_criteria_change)
        # Display selected questionaire
        if render:
            with self.out:
                clear_output()
                display(self.selectedQuestionaire.allWidgets)

    def render_selected(self):
        """Render the currently selected questionaire into the output area.

        Used by deferred loading: update(render=False) + set_all_values() build
        the state without rendering, then this performs the single final render.
        """
        with self.out:
            clear_output()
            display(self.selectedQuestionaire.allWidgets)

    def save_questionaires(self):
        file_dict = {}
        for criterion, questionaire_dict in self.allQuestionaires.items():
            questionaire = QuestionaireAndMatrix(parent=criterion)
            questionaire.comparisons_from_dict(criterion, questionaire_dict)
            file_dict[criterion] = questionaire.export(df_format='html', im_format='html')
        return file_dict
        
    def get_all_consistencies(self, precision=5):
        consistency_dict = {}
        for criterion, questionaire in self.allQuestionaires.items():
            ahp_compare = Compare(criterion, questionaire, precision=precision)
            consistency_dict[criterion] = ahp_compare.consistency_ratio
        return consistency_dict

    def export_matrices_and_figures(self, b):
        with self.downloadOut:
            clear_output()
            print('Preparing download...')
        filename = 'criteriaComparisons.zip'
        filename = os.path.join(tmp_dir, filename)
        file_dict = self.save_questionaires()
        file_list = [item for sublist in file_dict.values() for item in sublist]
        create_zip(filename, file_list)
        # with open(filename, 'rb') as f:
            # binarydata = f.read()
        # content_b64 = b64encode(binarydata).decode()
        # data_url = f'data:application/octet-stream;charset=utf-8;base64,{content_b64}'
        # js_code = f"""
            # var a = document.createElement('a');
            # a.setAttribute('download', '{filename}');
            # a.setAttribute('href', '{data_url}');
            # a.click()
        # """
        with self.downloadOut:
            clear_output()
            display(FileLink(filename))
            # display(HTML(f'<script>{js_code}</script>'))

    def on_level_change(self, change):
        if change['type'] == 'change' and change['name'] == 'value':
            self.criteriaSelector.options = self.get_criteria_options(int(change['new']))

    def on_criteria_change(self, change):
        #  print(change)
        if change['name'] == 'value':
            # Update the self.allQuestionaire dict of the previously selected questionaire
            self.allQuestionaires[change['old']] = self.selectedQuestionaire.comparisons_to_dict()
            if self.criteriaSelector.value:
                # Update the selectedQuestionaire displayed in the GUI
                self.selectedQuestionaire.comparisons_from_dict(
                        self.criteriaSelector.value,
                        self.allQuestionaires[self.criteriaSelector.value],
                        self.criteria_colors)

    def get_criteria_options(self, level=0):
        out = []
        if level == 0:
            #  print(self.tree.root)
            #  print(self.tree.ipytree_root.name)
            out.append(self.tree.ipytree_root.name)
        else:
            candidates = self.tree.get_node_names(level=level)
            #  print(candidates)
            for criteria in candidates:
                if len(self.tree.treelib_tree.children(criteria)) > 1:
                    out.append(criteria)
        return out

    def get_criteria_to_compare(self):
        out = []
        for level in range(self.tree.treelib_tree.depth()):
            candidates = self.tree.get_node_names(level=level)
            #  print(candidates)
            for criteria in candidates:
                if len(self.tree.treelib_tree.children(criteria)) > 1:
                    out.append(criteria)
        return out

    def get_level_options(self):
        levels = []
        for level in range(self.tree.treelib_tree.depth()):
            #  print('get_level_options.level={}'.format(level))
            for nodename in self.tree.get_node_names(level=level):
                #  print('get_level_options.nodename={}'.format(nodename))
                #  print('get_level_options.children={}'.format(self.tree.treelib_tree.children(nodename)))
                if len(self.tree.treelib_tree.children(nodename)) > 1:
                    levels.append(str(level))
                    break
        #  print(levels)
        return levels

    def comparisons_to_dict(self, parent=None):
        out = {}
        if parent:
            #  out[parent] = self.allQuestionaires[parent].comparisons_to_dict()
            out[parent] = self.allQuestionaires[parent]
        else:
            for parent, compare in self.allQuestionaires.items():
                #  out[parent] = self.allQuestionaires[parent].comparisons_to_dict()
                out[parent] = self.allQuestionaires[parent]
        return out

    def get_compare_objects(self, precision=5):
        out = {}
        for parent, questionaire in self.allQuestionaires.items():
            ahp_compare = Compare(parent, questionaire, precision=precision)
            out[parent] = ahp_compare
        return out

    def get_all_outputs(self):
        data = {
                tab_titles[3]: self.comparisons_to_dict()
                }
        return data

    def set_all_values(self, data):
        for key, item in data[tab_titles[3]].items():
            # Skip saved comparisons whose parent no longer exists in the current
            # criteria tree (e.g. a .smt where the tree was renamed/edited but the
            # comparisons kept old placeholder names). update() already built the
            # valid questionaires from the tree; only overwrite those.
            if key not in self.allQuestionaires:
                continue
            self.allQuestionaires[key] = item
            if key == self.criteriaSelector.value:
                self.selectedQuestionaire.comparisons_from_dict(key, self.allQuestionaires[key])

