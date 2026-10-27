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
from .titleAndHelp import TitleAndHelp
from .constants import tmp_dir
from .utilities import get_loading_bar
from .questionaireAndMatrix import QuestionaireAndMatrix
from .combinedTree import CombinedTree
from .utilities import create_zip
from .ahp import Compare

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Tuesday Jul 09, 2024 15:55:36 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Wednesday Nov 20, 2024 16:45:58 CET'

#    TODO: 
#           Add things to do here

loading_bar = get_loading_bar()

class RatingScaleComparator():
    def __init__(self):
        self.tree = None
        self.alternatives = None
        self.title = TitleAndHelp('Perform the pairwise comparison of the items in the Rating Scale', 'docs/help_ratingScaleComparator.html')
        self.out = widgets.Output()
        self.downloadOut = widgets.Output()
        self.criteriaSelector = widgets.Select(
                #  options=self.criteriaOptions,
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

        self.allQuestionaires = {}
        self.criteriaOptions = []

        self.allWidgets = widgets.VBox([
                self.title.allWidgets,
                self.criteriaSelector,
                self.out,
                self.exportButton,
                self.downloadOut
            ])
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

    def update(self, tree_dict, rating_scales, silent=False):
        # print('ratingScaleComparator.update.rating_scales={}'.format(rating_scales))
        if not silent:
            with self.out:
                clear_output()
                display(loading_bar)
        # Update tree object
        self.tree = CombinedTree()
        self.tree.from_dict(tree_dict)
        self.rating_scales = rating_scales
        self.criteriaOptions = [n.identifier for n in self.tree.treelib_tree.leaves() if not rating_scales[n.identifier][-1]]
        #  self.criteriaSelector.options = self.criteriaOptions
        #  self.criteriaSelector.value = self.criteriaOptions[0]
        # Remove questionaires for criteria that have been removed
        self.allQuestionaires = {key:self.allQuestionaires[key] for key in self.criteriaOptions if key in self.allQuestionaires}
        for criterion in self.criteriaOptions:
            children = [node.identifier for node in self.tree.treelib_tree.children(criterion)]
            if criterion not in self.allQuestionaires.keys():
            # Add questionaires for new criteria
                #  self.allQuestionaires[criterion] = QuestionaireAndMatrix(criteria_list=self.rating_scales[criterion][:-1], parent=criterion)
                self.allQuestionaires[criterion] = self.build_new_questionaire(self.rating_scales[criterion][:-1])
            else:
            # Update questionaires for already existing criteria
                #  self.allQuestionaires[criterion].update(self.rating_scales[criterion][:-1])
                self.allQuestionaires[criterion] = self.update_existing_questionaire(criterion, self.rating_scales[criterion][:-1])
        #  self.selectedQuestionaire = self.allQuestionaires[self.criteriaOptions[0]]
        self.selectedQuestionaire = QuestionaireAndMatrix()
        self.selectedQuestionaire.comparisons_from_dict(
                self.criteriaOptions[0],
                self.allQuestionaires[self.criteriaOptions[0]])
        # Unlink actions to functions
        self.criteriaSelector.unobserve(self.on_criteria_change)
        # Update questionaire selectors
        self.criteriaSelector.options = self.criteriaOptions
        self.criteriaSelector.value = self.criteriaOptions[0]
        # Link actions to functions again
        self.criteriaSelector.observe(self.on_criteria_change)
        # Display selected questionaire
        if not silent:
            with self.out:
                clear_output()
                display(self.selectedQuestionaire.allWidgets)

    def save_questionaires(self):
        file_dict = {}
        for criterion, questionaire_dict in self.allQuestionaires.items():
            questionaire = QuestionaireAndMatrix(parent=criterion)
            questionaire.comparisons_from_dict(criterion, questionaire_dict)
            file_dict[criterion] = questionaire.export(df_format='html', im_format='html')
            #  file_list.extend(self.allQuestionaires[criterion].export())
        return file_dict

    def export_matrices_and_figures(self, b):
        with self.downloadOut:
            clear_output()
            print('Preparing file...')
        filename = 'ratingComparisons.zip'
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

    def on_criteria_change(self, change):
        #  print(change)
        if change['name'] == 'value':
            # Update the self.allQuestionaire dict of the previously selected questionaire
            self.allQuestionaires[change['old']] = self.selectedQuestionaire.comparisons_to_dict()
            if self.criteriaSelector.value:
                # Update the selectedQuestionaire displayed in the GUI
                self.selectedQuestionaire.comparisons_from_dict(
                        self.criteriaSelector.value,
                        self.allQuestionaires[self.criteriaSelector.value])

    def get_criteria_options(self):
        out = [n.identifier for n in self.tree.treelib_tree.leaves()]
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
        for parent, compare in self.allQuestionaires.items():
            ahp_compare = Compare(parent, compare, precision=precision)
            out[parent] = ahp_compare
        return out

    def get_all_outputs(self):
        return self.comparisons_to_dict()

    def set_all_values(self, data):
        for key, item in data.items():
            # Skip saved data for subcriteria no longer in the tree (renamed/edited .smt).
            if key not in self.allQuestionaires:
                continue
            self.allQuestionaires[key] = item
            if key == self.criteriaSelector.value:
                self.selectedQuestionaire.comparisons_from_dict(key, self.allQuestionaires[key])
