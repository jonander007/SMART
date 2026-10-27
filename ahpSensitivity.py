#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ipywidgets as widgets
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
import itertools
from collections import OrderedDict
from IPython.display import display, HTML, clear_output
from IPython.display import FileLink
from scipy.stats import rankdata

from .titleAndHelp import TitleAndHelp
from .constants import (text_fontdict, tmp_dir, tab_titles,
                        perturbation_choices, write_html_config)
from .utilities import (get_loading_bar, validate_inputs,
                        create_zip, make_violin_fig, make_box_fig,
                        make_heatmap_fig)
from .notificationBar import NotificationBar
from .ahp import Compose
from .combinedTree import CombinedTree
from .smtReport import generate_compare_objects

__CREATION_DATE__ = 'Tuesday Jul 09, 2024'
__LAST_MODIFIED__  = 'Sunday Jun 01, 2026'

TAB = 6
TAB_TITLE = tab_titles[TAB]

loading_bar = get_loading_bar()

# ─────────────────────────────────────────────────────────────────────────────
# SAATY SCALE — discrete values
# ─────────────────────────────────────────────────────────────────────────────
# Ordered from most-favouring-first-element (9) to most-favouring-second (1/9)
SAATY_LABELS = ['9', '8', '7', '6', '5', '4', '3', '2', '1',
                '1/2', '1/3', '1/4', '1/5', '1/6', '1/7', '1/8', '1/9']
SAATY_VALUES = [9, 8, 7, 6, 5, 4, 3, 2, 1,
                1/2, 1/3, 1/4, 1/5, 1/6, 1/7, 1/8, 1/9]
SAATY_LABEL_TO_VALUE = dict(zip(SAATY_LABELS, SAATY_VALUES))
SAATY_VALUE_TO_LABEL = {round(v, 6): k for k, v in zip(SAATY_LABELS, SAATY_VALUES)}


def saaty_range(from_label, to_label):
    """
    Return the list of discrete Saaty values between two labels (inclusive),
    in scale order. E.g. saaty_range('1/3', '5') ->
    [1/3, 1/2, 1, 2, 3, 4, 5] mapped through the canonical 17-point order.
    """
    i_from = SAATY_LABELS.index(from_label)
    i_to   = SAATY_LABELS.index(to_label)
    lo, hi = sorted([i_from, i_to])
    return [(SAATY_LABELS[i], SAATY_VALUES[i]) for i in range(lo, hi + 1)]


# ─────────────────────────────────────────────────────────────────────────────
# PARAMETRIC SENSITIVITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _renormalize_weights(base_weights, criterion, new_value):
    w = dict(base_weights)
    others = {k: v for k, v in w.items() if k != criterion}
    total_others = sum(others.values())
    remaining = 1.0 - new_value
    if total_others > 1e-12:
        factor = remaining / total_others
        for k in others:
            w[k] = others[k] * factor
    else:
        n = len(others)
        for k in others:
            w[k] = remaining / n if n > 0 else 0.0
    w[criterion] = new_value
    return w


def _compute_scores(rating_table, weights):
    cols = [c for c in rating_table.columns if c in weights]
    if not cols:
        return {}
    w_vec = np.array([weights[c] for c in cols])
    w_sum = w_vec.sum()
    if w_sum > 1e-12:
        w_vec = w_vec / w_sum
    scores = {}
    for alt in rating_table.index:
        row = np.array([rating_table.loc[alt, c] for c in cols])
        scores[alt] = float(np.dot(row, w_vec))
    return scores


class PairwiseRow:
    """
    A sweep row for a single pairwise comparison along the discrete Saaty scale.
    The user picks (parent, pair) and a Saaty range [from .. to]; the sweep walks
    every discrete Saaty value in that range, recomputing AHP weights each step.
    """
    def __init__(self, pair_options, on_remove, idx, on_change=None):
        # pair_options: list of (label, key) where key = (parent, (A, B))
        self.on_remove = on_remove
        self.on_change = on_change
        self.idx = idx
        self.pairSelector = widgets.Dropdown(
            options=pair_options,
            value=pair_options[0][1] if pair_options else None,
            description='Comparison:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='340px'),
        )
        self.fromSel = widgets.Dropdown(
            options=SAATY_LABELS, value='1/3',
            description='From:', style={'description_width': 'initial'},
            layout=widgets.Layout(width='130px'),
        )
        self.toSel = widgets.Dropdown(
            options=SAATY_LABELS, value='5',
            description='To:', style={'description_width': 'initial'},
            layout=widgets.Layout(width='130px'),
        )
        self.removeBtn = widgets.Button(
            description='✕', button_style='danger',
            layout=widgets.Layout(width='36px', height='28px'),
        )
        self.removeBtn.on_click(lambda _: self.on_remove(self.idx))
        if on_change:
            self.fromSel.observe(lambda _: on_change(), names='value')
            self.toSel.observe(lambda _: on_change(), names='value')
        self.row = widgets.HBox(
            [self.pairSelector, self.fromSel, self.toSel, self.removeBtn],
            layout=widgets.Layout(gap='8px', align_items='center'),
        )

    def get_config(self):
        steps = saaty_range(self.fromSel.value, self.toSel.value)
        return {
            'mode': 'pairwise',
            'pair_key': self.pairSelector.value,
            'from': self.fromSel.value,
            'to': self.toSel.value,
            'steps': steps,           # list of (label, value)
            'n_steps': len(steps),
        }


class WeightRow:
    """
    A sweep row for a criterion's global weight over discrete user-defined values.
    The user picks a criterion and a min/max weight plus number of steps; the
    sweep walks each discrete weight, renormalizing the others proportionally.
    """
    def __init__(self, criterion_names, on_remove, idx, on_change=None):
        self.on_remove = on_remove
        self.on_change = on_change
        self.idx = idx
        self.criterionSelector = widgets.Dropdown(
            options=criterion_names,
            value=criterion_names[0] if criterion_names else None,
            description='Criterion:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='280px'),
        )
        self.minText = widgets.BoundedFloatText(
            value=0.05, min=0.001, max=0.999, step=0.01,
            description='Min:', style={'description_width': 'initial'},
            layout=widgets.Layout(width='140px'),
        )
        self.maxText = widgets.BoundedFloatText(
            value=0.50, min=0.001, max=0.999, step=0.01,
            description='Max:', style={'description_width': 'initial'},
            layout=widgets.Layout(width='140px'),
        )
        self.stepsSlider = widgets.IntSlider(
            value=5, min=2, max=20, step=1,
            description='Steps:', style={'description_width': 'initial'},
            layout=widgets.Layout(width='200px'),
        )
        self.removeBtn = widgets.Button(
            description='✕', button_style='danger',
            layout=widgets.Layout(width='36px', height='28px'),
        )
        self.removeBtn.on_click(lambda _: self.on_remove(self.idx))
        if on_change:
            self.stepsSlider.observe(lambda _: on_change(), names='value')
        self.row = widgets.HBox(
            [self.criterionSelector, self.minText, self.maxText,
             self.stepsSlider, self.removeBtn],
            layout=widgets.Layout(gap='8px', align_items='center'),
        )

    def get_config(self):
        import numpy as _np
        vals = list(_np.linspace(self.minText.value, self.maxText.value,
                                 self.stepsSlider.value))
        return {
            'mode': 'weight',
            'criterion': self.criterionSelector.value,
            'min': self.minText.value,
            'max': self.maxText.value,
            'steps': vals,
            'n_steps': len(vals),
        }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class AhpSensitivity:
    """
    Tab 6 — Sensitivity Analysis

    Two modes selectable via toggle:
      • Monte Carlo  — random perturbation of weights / scores (original)
      • Parametric   — systematic sweep of selected criteria weight ranges
    """

    def __init__(self, logger, rating_table=None, weights=None):
        self.logger = logger
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Initializing')

        # shared state
        self.rating_table  = rating_table
        self.weights       = weights
        self.plots         = []
        self.labels        = []
        self.base_weights  = {}
        self.alternatives  = []
        self.criteria      = []
        self._param_rows   = []
        self._result_df    = None

        # Monte Carlo state
        self.scores_array  = None
        self.ranks_array   = None

        # ── Notification bar ──────────────────────────────────────────
        self.notif = NotificationBar()

        # ── Title ─────────────────────────────────────────────────────
        self.title = TitleAndHelp('Sensitivity Analysis',
                                  'docs/help_ahpCalculator.html')

        # ── Mode toggle ───────────────────────────────────────────────
        self.modeToggle = widgets.ToggleButtons(
            options=[('🎲  Monte Carlo', 'mc'),
                     ('📐  Parametric sweep', 'param')],
            value='mc',
            style={'description_width': 'initial',
                   'button_width': '200px'},
        )
        self.modeToggle.observe(self._on_mode_change, names='value')

        # ── Output areas ──────────────────────────────────────────────
        self.plotsOut    = widgets.Output()
        self.downloadOut = widgets.Output()

        # ── MC widgets ────────────────────────────────────────────────
        self.nsimSlider = widgets.IntSlider(
            value=10000, min=1000, max=1000000, step=1,
            description='Monte Carlo iterations',
            readout=True, readout_format='d',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='500px'),
        )
        self.sigmaSlider = widgets.FloatSlider(
            value=0.15, min=0.01, max=1.0, step=0.01,
            description='Perturbation σ',
            readout=True, readout_format='.2f',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='500px'),
        )
        self.perturbationSelector = widgets.SelectMultiple(
            options=perturbation_choices,
            value=perturbation_choices,
            description='Perturb:',
            style={'description_width': 'initial'},
        )
        self.mcRunBtn = widgets.Button(
            description='▶ Run Monte Carlo',
            button_style='success',
            layout=widgets.Layout(width='200px'),
        )
        self.mcExportBtn = widgets.Button(
            description='Export figures',
            button_style='',
            layout=widgets.Layout(width='150px'),
        )
        self.mcRunBtn.on_click(self._run_mc)
        self.mcExportBtn.on_click(self._export_mc)

        self._mcPanel = widgets.VBox([
            self.nsimSlider,
            self.sigmaSlider,
            self.perturbationSelector,
            self.mcRunBtn,
            self.plotsOut,
            self.mcExportBtn,
            self.downloadOut,
        ])

        # ── Parametric widgets ────────────────────────────────────────
        self._paramInfoLabel = widgets.HTML(
            value='<i style="color:#888">Load a case first (navigate to '
                  'Results tab), then configure parameters.</i>'
        )

        # Sub-mode: sweep pairwise comparisons (Saaty) or criterion weights
        self._sweepKind = widgets.ToggleButtons(
            options=[('Pairwise comparison (Saaty scale)', 'pairwise'),
                     ('Criterion weight', 'weight')],
            value='pairwise',
            style={'description_width': 'initial', 'button_width': '260px'},
        )
        self._sweepKind.observe(self._on_sweep_kind_change, names='value')

        self._pairwiseHeader = widgets.HTML(
            value='<div style="display:flex;gap:8px;font-size:11px;'
                  'color:#888;font-weight:600;text-transform:uppercase;'
                  'letter-spacing:.05em;padding:4px 0">'
                  '<span style="width:340px">Comparison (A vs B)</span>'
                  '<span style="width:130px">From</span>'
                  '<span style="width:130px">To</span>'
                  '</div>'
        )
        self._weightHeader = widgets.HTML(
            value='<div style="display:flex;gap:8px;font-size:11px;'
                  'color:#888;font-weight:600;text-transform:uppercase;'
                  'letter-spacing:.05em;padding:4px 0">'
                  '<span style="width:280px">Criterion</span>'
                  '<span style="width:140px">Min</span>'
                  '<span style="width:140px">Max</span>'
                  '<span style="width:200px">Steps</span>'
                  '</div>'
        )
        self._weightHeader.layout.display = 'none'

        self._paramsBox  = widgets.VBox([],
                                        layout=widgets.Layout(gap='6px'))
        self._addParamBtn = widgets.Button(
            description='+ Add comparison',
            button_style='info', icon='plus',
            layout=widgets.Layout(width='180px'),
        )
        self._addParamBtn.on_click(self._on_add_param)

        self._paramRunBtn = widgets.Button(
            description='▶ Run parametric sweep',
            button_style='success',
            layout=widgets.Layout(width='220px'),
        )
        self._paramRunBtn.on_click(self._run_parametric)

        self._comboLabel  = widgets.HTML(value='')
        self._paramResultsOut = widgets.Output()
        self._paramDownloadOut = widgets.Output()
        self._paramExportBtn = widgets.Button(
            description='Export CSV', button_style='',
            icon='download', disabled=True,
            layout=widgets.Layout(width='140px'),
        )
        self._paramExportBtn.on_click(self._export_parametric)

        self._paramPanel = widgets.VBox([
            self._paramInfoLabel,
            widgets.HTML('<hr style="margin:8px 0">'),
            self._sweepKind,
            self._pairwiseHeader,
            self._weightHeader,
            self._paramsBox,
            self._addParamBtn,
            widgets.HTML('<hr style="margin:8px 0">'),
            widgets.HBox([self._paramRunBtn, self._comboLabel],
                         layout=widgets.Layout(align_items='center',
                                               gap='12px')),
            self._paramResultsOut,
            widgets.HBox([self._paramExportBtn]),
            self._paramDownloadOut,
        ])
        self._paramPanel.layout.display = 'none'

        # ── Final layout ──────────────────────────────────────────────
        self.allWidgets = widgets.VBox([
            self.notif.widget,
            self.title.allWidgets,
            self.modeToggle,
            widgets.HTML('<hr style="margin:6px 0">'),
            self._mcPanel,
            self._paramPanel,
        ])

    # ── Mode switch ───────────────────────────────────────────────────

    def _on_mode_change(self, change):
        if change['new'] == 'mc':
            self._mcPanel.layout.display    = ''
            self._paramPanel.layout.display = 'none'
        else:
            self._mcPanel.layout.display    = 'none'
            self._paramPanel.layout.display = ''

    # ── Public update ─────────────────────────────────────────────────

    def update(self, tree_dict, criteria_compares_dict,
               alternatives_names, alternatives_compares_dict):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Updating')
        if len(self.plots) > 0:
            with self.plotsOut:
                clear_output()
                display(loading_bar)

        self.invalid = validate_inputs(
            self.notif, tree_dict, criteria_compares_dict,
            alternatives_names, alternatives_compares_dict)

        if not self.invalid:
            tree = CombinedTree()
            tree.from_dict(tree_dict)
            self._raw_criteria_dict = criteria_compares_dict  # keep raw for sweeps
            self.criteria_compares = generate_compare_objects(
                criteria_compares_dict)
            self.alternatives_names = alternatives_names[:-1]

            if alternatives_names[-1] == 'Pairwise Comparison':
                self.alternatives_compares = generate_compare_objects(
                    alternatives_compares_dict)
            else:
                self.alternatives_compares = generate_compare_objects(
                    alternatives_compares_dict, is_rating_scale=True)

            self.criteria_names = list(self.alternatives_compares.keys())
            self.compose = Compose()
            self.compose.add_comparisons(
                list(self.criteria_compares.values()) +
                list(self.alternatives_compares.values()))
            self.compose.add_hierarchy(tree.get_hierarchy())
            self.weights      = self._get_criteria_weights(tree)
            self.rating_table = self._get_weighted_scores('local_weights')

            # ── Parametric: build base weights ────────────────────────
            self.tree      = tree
            self.criteria  = list(self.alternatives_compares.keys())
            self.alternatives = self.alternatives_names

            depth  = tree.treelib_tree.depth()
            leaves = list(tree.treelib_tree.filter_nodes(
                lambda n: n.is_leaf(tree.treelib_tree.identifier)))
            all_w  = {}
            for level in reversed(range(1, depth)):
                for node in tree.get_node_names(level=level):
                    if tree.get_treelib_node(node) not in leaves:
                        cmp = self.compose._get_node(node)
                        all_w |= cmp.global_weights
            self.base_weights = {c: all_w.get(c, 0.0) for c in self.criteria}
            total = sum(self.base_weights.values())
            if total > 1e-12:
                self.base_weights = {k: v/total
                                     for k, v in self.base_weights.items()}

            self._refresh_param_options()
            # Build pairwise comparison options: (label, (parent, (A,B)))
            self._pair_options = []
            for parent, pairs in (criteria_compares_dict or {}).items():
                for pair_key in pairs.keys():
                    if isinstance(pair_key, tuple) and len(pair_key) == 2:
                        a, b = pair_key
                        label = f'{parent}:  {a}  vs  {b}'
                        self._pair_options.append((label, (parent, pair_key)))
            self._refresh_pair_options()
            self._paramInfoLabel.value = (
                f'<span style="color:#16a34a">✓ Case loaded — '
                f'{len(self.alternatives)} alternatives, '
                f'{len(self.criteria)} criteria.</span>'
            )

    # ─────────────────────────────────────────────────────────────────
    # MONTE CARLO
    # ─────────────────────────────────────────────────────────────────

    def _run_mc(self, b):
        if self.rating_table is None or self.weights is None:
            self.notif.error(
                'No data available. Navigate to Results first.')
            return
        if self.scores_array is not None:
            del self.scores_array
        if self.ranks_array is not None:
            del self.ranks_array
        with self.plotsOut:
            clear_output()
            display(loading_bar)
        alternatives        = self.rating_table.index.tolist()
        original_rt         = self.rating_table.values
        all_scores, all_ranks = [], []
        np.random.seed()
        n_sim    = self.nsimSlider.value
        perturbed = self.perturbationSelector.value
        sigma    = self.sigmaSlider.value
        w_vec    = self.weights['Weight']
        for _ in range(n_sim):
            rt = original_rt.copy()
            if 'matrix' in perturbed:
                noise = np.random.normal(0, sigma, rt.shape)
                rt    = np.clip(rt + noise, 0, 1)
            w = w_vec.copy()
            if 'weights' in perturbed:
                noise = np.random.normal(0, sigma, len(w))
                w     = np.clip(w + noise, 0, 1)
                w     = w / w.sum()
            norm   = rt / original_rt.max(axis=0)
            scores = norm @ w
            ranks  = rankdata(-scores, method='ordinal')
            all_scores.append(scores)
            all_ranks.append(ranks)
        self.scores_array     = np.array(all_scores)
        self.ranks_array      = np.array(all_ranks)
        self.alternatives_names_mc = alternatives
        self._generate_mc_plots()
        self._log_run({
            'type':         'Monte Carlo',
            'n_iterations': n_sim,
            'sigma':        sigma,
            'perturbed':    list(perturbed),
        })

    def _generate_mc_plots(self):
        del self.plots, self.labels
        self.plots, self.labels = [], []
        alts = self.alternatives_names_mc
        for fig_fn, label in [
            (make_violin_fig,  'Monte Carlo Ranking Distribution'),
            (make_box_fig,     'Monte Carlo Scores Distribution'),
            (make_heatmap_fig, 'Ranking Probability Heatmap'),
        ]:
            arr = (self.ranks_array if 'Ranking' in label or 'Heatmap' in label
                   else self.scores_array)
            self.labels.append(widgets.Label(
                value=label, style=dict(font_weight='bold')))
            self.plots.append(go.FigureWidget(fig_fn(arr, alts)))
        with self.plotsOut:
            clear_output()
            display(widgets.VBox(
                [v for pair in zip(self.labels, self.plots) for v in pair]))

    def _export_mc(self, b):
        with self.downloadOut:
            clear_output()
            self.notif.info('Preparing download...')
        file_dict = {}
        for i, plot in enumerate(self.plots):
            fn = os.path.join(
                tmp_dir,
                '{}.html'.format(self.labels[i].value.replace(' ', '_')))
            fig = go.Figure(plot.to_plotly_json())
            fig.write_html(fn, full_html=False, config=write_html_config)
            file_dict[self.labels[i].value] = fn
        zf = os.path.join(tmp_dir, 'sensitivities.zip')
        create_zip(zf, list(file_dict.values()))
        with self.downloadOut:
            clear_output()
            display(FileLink(zf))
        self.notif.success('Figures exported.')

    # ─────────────────────────────────────────────────────────────────
    # PARAMETRIC SWEEP
    # ─────────────────────────────────────────────────────────────────

    def _refresh_param_options(self):
        for pr in self._param_rows:
            if isinstance(pr, WeightRow):
                pr.criterionSelector.options = self.criteria
        self._update_combo_count()

    def _refresh_pair_options(self):
        opts = getattr(self, '_pair_options', [])
        for pr in self._param_rows:
            if isinstance(pr, PairwiseRow):
                pr.pairSelector.options = opts
        self._update_combo_count()

    def _on_sweep_kind_change(self, change):
        # Switching kind clears existing rows (they're of the other type)
        self._param_rows = []
        self._paramsBox.children = []
        is_pair = change['new'] == 'pairwise'
        self._pairwiseHeader.layout.display = '' if is_pair else 'none'
        self._weightHeader.layout.display   = 'none' if is_pair else ''
        self._addParamBtn.description = ('+ Add comparison' if is_pair
                                         else '+ Add criterion')
        self._update_combo_count()

    def _on_add_param(self, _b):
        kind = self._sweepKind.value
        idx = len(self._param_rows)
        if kind == 'pairwise':
            if not getattr(self, '_pair_options', None):
                self.notif.error('Load a case first.')
                return
            pr = PairwiseRow(self._pair_options, self._on_remove_param,
                             idx, on_change=self._update_combo_count)
        else:
            if not self.criteria:
                self.notif.error('Load a case first.')
                return
            pr = WeightRow(self.criteria, self._on_remove_param,
                           idx, on_change=self._update_combo_count)
        self._param_rows.append(pr)
        self._paramsBox.children = [p.row for p in self._param_rows]
        self._update_combo_count()

    def _on_remove_param(self, idx):
        self._param_rows = [pr for pr in self._param_rows
                            if pr.idx != idx]
        for i, pr in enumerate(self._param_rows):
            pr.idx = i
        self._paramsBox.children = [pr.row for pr in self._param_rows]
        self._update_combo_count()

    def _update_combo_count(self):
        if not self._param_rows:
            self._comboLabel.value = ''
            return
        total = 1
        for pr in self._param_rows:
            total *= pr.get_config()['n_steps']
        color = '#d32f2f' if total > 10000 else '#888'
        self._comboLabel.value = (
            f'<span style="font-size:13px;color:{color}">'
            f'{total:,} combinations</span>'
        )

    def _weights_from_modified_pairs(self, overrides):
        """
        Recompute leaf-criteria global weights after overriding specific
        pairwise comparison values.
        overrides: dict {(parent, (A,B)): saaty_value}
        Returns: dict {leaf_criterion: global_weight} renormalized to sum 1.
        """
        # Deep-copy the raw comparison dict and apply overrides
        import copy
        raw = copy.deepcopy(self._raw_criteria_dict)
        for (parent, pair_key), val in overrides.items():
            if parent in raw and pair_key in raw[parent]:
                raw[parent][pair_key] = val

        # Rebuild Compare objects + Compose to get fresh global weights
        criteria_compares = generate_compare_objects(raw)
        compose = Compose()
        compose.add_comparisons(
            list(criteria_compares.values()) +
            list(self.alternatives_compares.values()))
        compose.add_hierarchy(self.tree.get_hierarchy())

        depth  = self.tree.treelib_tree.depth()
        leaves = list(self.tree.treelib_tree.filter_nodes(
            lambda n: n.is_leaf(self.tree.treelib_tree.identifier)))
        all_w  = {}
        for level in reversed(range(1, depth)):
            for node in self.tree.get_node_names(level=level):
                if self.tree.get_treelib_node(node) not in leaves:
                    cmp = compose._get_node(node)
                    all_w |= cmp.global_weights
        w = {c: all_w.get(c, 0.0) for c in self.criteria}
        total = sum(w.values())
        if total > 1e-12:
            w = {k: v/total for k, v in w.items()}
        return w

    def _run_parametric(self, _b):
        self.notif.clear()
        if self.rating_table is None:
            self.notif.error(
                'No case loaded. Navigate to Results tab first.')
            return
        if not self._param_rows:
            self.notif.error('Add at least one parameter.')
            return

        with self._paramResultsOut:
            clear_output()
            display(loading_bar)

        configs = [pr.get_config() for pr in self._param_rows]
        kind = self._sweepKind.value

        # Validate no duplicates
        if kind == 'pairwise':
            keys = [c['pair_key'] for c in configs]
        else:
            keys = [c['criterion'] for c in configs]
        if len(keys) != len(set(keys)):
            self.notif.error(
                'Duplicate parameter — each can only appear once.')
            with self._paramResultsOut:
                clear_output()
            return

        # Build the discrete grids (list of values per parameter)
        grids = [c['steps'] for c in configs]   # each is list
        combos = list(itertools.product(*grids))
        rows = []

        for combo in combos:
            if kind == 'pairwise':
                # combo is a tuple of (label, value) pairs
                overrides = {cfg['pair_key']: val
                             for cfg, (lbl, val) in zip(configs, combo)}
                w = self._weights_from_modified_pairs(overrides)
                row = {self._pair_col(cfg): lbl
                       for cfg, (lbl, val) in zip(configs, combo)}
            else:
                w = dict(self.base_weights)
                for cfg, val in zip(configs, combo):
                    w = _renormalize_weights(w, cfg['criterion'], val)
                row = {cfg['criterion']: round(val, 4)
                       for cfg, val in zip(configs, combo)}

            scores = _compute_scores(self.rating_table, w)
            if not scores:
                continue
            ranks = {alt: int(r) for alt, r in zip(
                scores.keys(),
                rankdata([-scores[a] for a in scores.keys()],
                         method='min'))}
            row.update({f'score_{a}': round(scores[a], 4)
                        for a in self.alternatives})
            row.update({f'rank_{a}': ranks[a] for a in self.alternatives})
            rows.append(row)

        self._result_df = pd.DataFrame(rows)
        self._paramExportBtn.disabled = False
        self._render_parametric(configs, kind)

        if kind == 'pairwise':
            log_params = [
                {'comparison': self._pair_col(c),
                 'from': c['from'], 'to': c['to'], 'n_steps': c['n_steps']}
                for c in configs]
        else:
            log_params = [
                {'criterion': c['criterion'], 'min': c['min'],
                 'max': c['max'], 'n_steps': c['n_steps']}
                for c in configs]
        self._log_run({
            'type':           'Parametric',
            'sweep_kind':     kind,
            'n_combinations': len(combos),
            'parameters':     log_params,
        })

    @staticmethod
    def _pair_col(cfg):
        """Readable column name for a pairwise sweep config."""
        parent, (a, b) = cfg['pair_key']
        return f'{a} vs {b}'

    def _render_parametric(self, configs, kind='weight'):
        df     = self._result_df
        alts   = self.alternatives
        if kind == 'pairwise':
            p_cols = [self._pair_col(c) for c in configs]
        else:
            p_cols = [c['criterion'] for c in configs]
        figs   = []

        if len(p_cols) == 1:
            p = p_cols[0]
            is_pair = (kind == 'pairwise')
            x_title = (f'Saaty judgment — {p}' if is_pair
                       else f'Weight of {p}')
            # For pairwise, enforce Saaty scale order on the x-axis
            xaxis_cfg = {}
            if is_pair:
                ordered = [lbl for lbl in SAATY_LABELS
                           if lbl in set(df[p].astype(str))]
                xaxis_cfg = dict(categoryorder='array',
                                 categoryarray=ordered)
            fig_s = go.Figure()
            fig_r = go.Figure()
            for a in alts:
                fig_s.add_trace(go.Scatter(
                    x=df[p].astype(str) if is_pair else df[p],
                    y=df[f'score_{a}'],
                    mode='lines+markers', name=a, line=dict(width=2)))
                fig_r.add_trace(go.Scatter(
                    x=df[p].astype(str) if is_pair else df[p],
                    y=df[f'rank_{a}'],
                    mode='lines+markers', name=a, line=dict(width=2)))
            fig_s.update_layout(
                title=f'Score sensitivity — {p}',
                xaxis_title=x_title, yaxis_title='Score',
                xaxis=xaxis_cfg,
                height=420, font=text_fontdict,
                legend=dict(orientation='h', yanchor='bottom', y=1.02))
            fig_r.update_layout(
                title=f'Rank sensitivity — {p}',
                xaxis_title=x_title,
                xaxis=xaxis_cfg,
                yaxis=dict(title='Rank', autorange='reversed',
                           tickmode='linear', tick0=1, dtick=1),
                height=420, font=text_fontdict,
                legend=dict(orientation='h', yanchor='bottom', y=1.02))
            figs += [go.FigureWidget(fig_s), go.FigureWidget(fig_r)]

        elif len(p_cols) == 2:
            p1, p2 = p_cols
            is_pair = (kind == 'pairwise')

            def _fmt_axis(vals):
                out = []
                for v in vals:
                    if isinstance(v, str):
                        out.append(v)
                    else:
                        out.append(f'{v:.3f}')
                return out

            for a in alts:
                pivot = df.pivot_table(
                    index=p1, columns=p2,
                    values=f'rank_{a}', aggfunc='mean')
                # Reorder Saaty-label axes into scale order
                if is_pair:
                    col_order = [l for l in SAATY_LABELS if l in pivot.columns]
                    row_order = [l for l in SAATY_LABELS if l in pivot.index]
                    if col_order:
                        pivot = pivot.reindex(columns=col_order)
                    if row_order:
                        pivot = pivot.reindex(index=row_order)
                fig = go.Figure(go.Heatmap(
                    z=pivot.values,
                    x=_fmt_axis(pivot.columns),
                    y=_fmt_axis(pivot.index),
                    colorscale='RdYlGn_r',
                    zmin=1, zmax=len(alts),
                    text=pivot.values.astype(int),
                    texttemplate='%{text}',
                    colorbar=dict(title='Rank'),
                ))
                fig.update_layout(
                    title=f'Rank heatmap — {a}',
                    xaxis_title=p2, yaxis_title=p1,
                    height=420, font=text_fontdict)
                figs.append(go.FigureWidget(fig))

        else:
            total = len(df)
            stab  = {a: (df[f'rank_{a}'] == 1).sum() / total * 100
                     for a in alts}
            fig_b = go.Figure(go.Bar(
                x=list(stab.keys()), y=list(stab.values()),
                marker_color=['#16a34a' if v == max(stab.values())
                              else '#1565c0' for v in stab.values()],
                text=[f'{v:.1f}%' for v in stab.values()],
                textposition='outside',
            ))
            fig_b.update_layout(
                title='Rank-1 stability (% of all combinations)',
                xaxis_title='Alternative',
                yaxis=dict(title='% times ranked 1st', range=[0, 105]),
                height=420, font=text_fontdict)
            figs.append(go.FigureWidget(fig_b))

            score_data = [{'Alternative': a, 'Score': v}
                          for a in alts for v in df[f'score_{a}']]
            score_df = pd.DataFrame(score_data)
            fig_v = go.Figure()
            for a in alts:
                vals = score_df[score_df['Alternative'] == a]['Score']
                fig_v.add_trace(go.Violin(
                    y=vals, name=a, box_visible=True,
                    meanline_visible=True, points=False))
            fig_v.update_layout(
                title='Score distribution across all combinations',
                yaxis_title='Score', height=420, font=text_fontdict)
            figs.append(go.FigureWidget(fig_v))

        # Rank frequency table
        total = len(df)
        rows_html = ''
        for a in alts:
            rc   = df[f'rank_{a}'].value_counts().sort_index()
            cols = ''.join(
                f'<td style="text-align:center;background:'
                f'{"#e8f5e9" if r==1 else "#fff3e0" if r==2 else "#ffebee" if r==len(alts) else "#fff"}">'
                f'{rc.get(r,0)} <span style="color:#888;font-size:11px">'
                f'({rc.get(r,0)/total*100:.0f}%)</span></td>'
                for r in range(1, len(alts)+1)
            )
            rows_html += f'<tr><td style="font-weight:600">{a}</td>{cols}</tr>'

        hdrs = ''.join(f'<th style="text-align:center">Rank {r}</th>'
                       for r in range(1, len(alts)+1))
        table_html = (
            f'<div style="margin-top:1rem;font-size:13px">'
            f'<b>Rank frequency — {total:,} combinations</b>'
            f'<div style="overflow-x:auto;margin-top:6px">'
            f'<table style="border-collapse:collapse;width:100%">'
            f'<thead><tr><th style="text-align:left;padding:6px 8px">'
            f'Alternative</th>{hdrs}</tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div></div>'
        )

        with self._paramResultsOut:
            clear_output()
            display(widgets.VBox(figs))
            display(HTML(table_html))

    def _export_parametric(self, _b):
        if self._result_df is None:
            return
        path = os.path.join(tmp_dir, 'parametric_sensitivity.csv')
        self._result_df.to_csv(path, index=False)
        with self._paramDownloadOut:
            clear_output()
            display(FileLink(path))
        self.notif.success('CSV exported.')

    # ─────────────────────────────────────────────────────────────────
    # SHARED HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _get_criteria_weights(self, tree=None):
        if tree is None:
            tree = self.tree
        depth  = tree.treelib_tree.depth()
        leaves = list(tree.treelib_tree.filter_nodes(
            lambda n: n.is_leaf(tree.treelib_tree.identifier)))
        weights = {}
        for level in reversed(range(1, depth)):
            for node in tree.get_node_names(level=level):
                if tree.get_treelib_node(node) not in leaves:
                    weights |= self.compose._get_node(node).global_weights
        leaf_nodes = tree.treelib_tree.leaves()
        paths = []
        for leaf in leaf_nodes:
            path = tree.treelib_tree.rsearch(leaf.identifier)
            path_names = [
                tree.treelib_tree[nid].tag
                for nid in reversed(list(path))
                if tree.treelib_tree[nid].tag != tree.root
            ]
            paths.append(path_names)
        df = pd.DataFrame(paths)
        df.columns = [f'Level{i+1}' for i in range(df.shape[1])]
        df['Weight'] = df.apply(
            lambda row: weights.get(row.dropna().iloc[-1], None), axis=1)
        return df

    def _get_weighted_scores(self, weight_type='local_weights'):
        scores = {}
        for alt in self.alternatives_names:
            scores[alt] = {
                c: self.compose[c][weight_type][alt]
                for c in self.alternatives_compares.keys()
            }
        df = pd.DataFrame(scores).T
        df.to_csv('final_df.csv')
        return df

    # ── State (not persisted) ─────────────────────────────────────────

    def _log_run(self, run_info):
        """Forward sensitivity run info to AppAPI for report traceability."""
        try:
            import pywebview as _wv
            win = _wv.active_window()
            if win and hasattr(win, 'evaluate_js'):
                pass  # JS bridge not needed — use Python-side API directly
        except Exception:
            pass
        # Store locally so run-idom-smart.py can read before report generation
        if not hasattr(self, '_run_log'):
            self._run_log = []
        self._run_log.append(run_info)

    def get_run_log(self):
        return getattr(self, '_run_log', [])

    def get_all_outputs(self):
        return {}

    def set_all_values(self, data):
        pass
