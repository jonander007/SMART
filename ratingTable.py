#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/ratingTable.py
from collections import OrderedDict
import ipywidgets as widgets
import pandas as pd
from IPython.display import display, HTML, clear_output
from functools import partial
from .utilities import get_loading_bar, validate_combobox

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Thursday Sep 05, 2024 10:48:54 CEST'
__VERSION__ = '2.0.0'
__LAST_MODIFIED__ = 'Tuesday Jun 09, 2025'

loading_bar = get_loading_bar()


class RatingTable():
    """
    One column (one alternative) in the shared rating table.
    Keeps the selectors OrderedDict; rendering is handled by RatingTablesEditor.
    """

    def __init__(self, alternative):
        self.alternative = alternative
        self.label       = widgets.Label(value=alternative)
        self.selectors   = OrderedDict()   # subcriterion → Combobox | Text

    # ── update ────────────────────────────────────────────────────────────────

    def update(self, rating_options: dict):
        """Sync selectors to current rating_options without rebuilding existing ones."""
        # Drop removed subcriteria
        self.selectors = OrderedDict(
            {k: v for k, v in self.selectors.items() if k in rating_options}
        )

        for subcriterion, options in rating_options.items():
            is_quantitative = options[-1]  # last element is bool flag

            if subcriterion in self.selectors:
                sel = self.selectors[subcriterion]
                if is_quantitative:
                    if not isinstance(sel, widgets.Text):
                        self.selectors[subcriterion] = widgets.Text(
                            value='',
                            layout=widgets.Layout(width='100%')
                        )
                else:
                    if isinstance(sel, widgets.Text):
                        self.selectors[subcriterion] = widgets.Combobox(
                            options=options[:-1],
                            layout=widgets.Layout(width='100%')
                        )
                    else:
                        prev = sel.value
                        sel.options = options[:-1]
                        sel.value   = prev
                        validate_combobox(sel, prev)
            else:
                if is_quantitative:
                    self.selectors[subcriterion] = widgets.Text(
                        value='',
                        layout=widgets.Layout(width='100%')
                    )
                else:
                    self.selectors[subcriterion] = widgets.Combobox(
                        options=options[:-1],
                        layout=widgets.Layout(width='100%')
                    )

        self._observe_all()

    # ── validation ────────────────────────────────────────────────────────────

    def _observe_all(self):
        for sel in self.selectors.values():
            try:
                sel.unobserve(self._validate_input, names='value')
            except ValueError:
                pass
            sel.observe(self._validate_input, names='value')

    def _validate_input(self, change):
        sel = change['owner']
        if isinstance(sel, widgets.Combobox):
            validate_combobox(sel, change['new'])

    # ── data I/O ──────────────────────────────────────────────────────────────

    def export(self):
        df = pd.DataFrame({self.alternative.replace(' ', '_'): self.get_all_outputs()})
        return df.transpose()

    def get_all_outputs(self):
        return OrderedDict(
            {sub: sel.value for sub, sel in self.selectors.items()}
        )

    def set_all_values(self, data: dict, rating_options: dict):
        self.update(rating_options)
        for subcriterion, value in data.items():
            if subcriterion in self.selectors:
                self.selectors[subcriterion].value = value
