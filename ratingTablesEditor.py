#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from collections import OrderedDict
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from IPython.display import FileLink
import pandas as pd
from .titleAndHelp import TitleAndHelp
from .constants import tab_titles, tmp_dir
from .ratingTable import RatingTable
from .utilities import create_zip, get_loading_bar

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Friday Sep 06, 2024 19:32:17 CEST'
__VERSION__ = '3.0.0'
__LAST_MODIFIED__ = 'Sunday Jul 20, 2026'

loading_bar = get_loading_bar()

# ── Why pagination ───────────────────────────────────────────────────────────
# A full grid is N_alternatives x N_subcriteria live Combobox widgets. On a real
# case (9 x 22 = 198) that burst of ~200 comm_open messages over Voila's
# websocket cannot be registered reliably by the front-end, whatever the IOPub
# limits are, and the container fails with "HBoxModel not found" / the table
# never finishes loading. So we show ONE alternative at a time (its ~22 cells)
# with a dropdown to switch — the same one-at-a-time pattern the comparison tabs
# already use. Only the visible alternative has live widgets; every other
# alternative's values live in a plain-data cache (read by autosave/Results/
# export), so nothing is lost.

_TABLE_CSS = """
<style>
.rt-cell.widget-combobox,
.rt-cell.widget-text {
    box-sizing: border-box !important;
    width: 100% !important;
    min-height: 34px !important;
    padding: 3px 8px !important;
    display: flex !important;
    align-items: center !important;
    margin: 0 !important;
}
.rt-cell.widget-combobox input,
.rt-cell.widget-text input {
    font-size: 13px !important;
    padding: 4px 6px !important;
    border-radius: 3px !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
.rt-cell.invalid-rating input {
    border: 1.5px solid #e74c3c !important;
    background: #fdf2f2 !important;
}
.widget-hbox { align-items: stretch !important; }
</style>
"""

_HDR = (
    'background:#2C3E50;color:#fff;font-weight:600;'
    'font-size:13px;padding:9px 10px;text-align:center;'
)
_CELL = (
    'padding:4px 8px;font-size:13px;color:#2c3e50;'
    'border-bottom:1px solid #eee;min-height:34px;'
    'display:flex;align-items:center;'
)


class RatingTablesEditor():

    def __init__(self):
        self.rating_scales = None
        self.alternatives  = None

        # Plain-data value cache for ALL alternatives: {alt: {subcriterion: value}}.
        # Source of truth; only the *visible* alternative is also held as live
        # widgets (in self._current_rt). This keeps live widget count to one
        # alternative's worth of cells, avoiding the comm_open burst.
        self._value_cache = OrderedDict()
        self._built        = False
        self._current_alt  = None      # alternative currently shown as widgets
        self._current_rt   = None      # its RatingTable (live selectors)

        self.title = TitleAndHelp(
            'Rate the alternatives assigning a value in the Rating Scale'
            ' for each subcriteria',
            'docs/help_ratingTablesEditor.html',
        )

        self.altSelector = widgets.Dropdown(
            description='Alternative:',
            disabled=False,
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='auto', margin='0 0 8px 0'),
        )
        self.altSelector.observe(self._on_alt_change, names='value')

        self.out          = widgets.Output()
        self.downloadOut  = widgets.Output()
        self.exportButton = widgets.Button(
            description='Export Ratings to CSV',
            button_style='',
            tooltip='Export Ratings to CSV',
            style={'description_width': 'initial'},
        )
        self.exportButton.on_click(self.exportRatings)
        self.allWidgets = widgets.VBox([
            self.title.allWidgets,
            self.altSelector,
            self.out,
            self.exportButton,
            self.downloadOut,
        ])

    # ── deferred-render contract (used by alternativeRating) ───────────────────

    @property
    def _dirty(self):
        """True while the live table still needs building (inverse of _built)."""
        return not self._built

    def render_if_needed(self):
        """Build the live table if it hasn't been built yet (called when the
        Rating Table section becomes visible)."""
        if not self._built and self.rating_scales and self.alternatives:
            self.update(self.rating_scales, self.alternatives)

    # ── public ────────────────────────────────────────────────────────────────

    def update(self, rating_scales: dict, alternatives: list, silent: bool = False):
        """
        silent=True  (case loading / batch): store state only, build nothing.
        silent=False (section opened): build the live single-alternative view.
        """
        self.alternatives  = list(alternatives) if alternatives else []
        self.rating_scales = rating_scales

        if silent:
            self._built = False
            return

        with self.out:
            clear_output()
            display(loading_bar)

        # Pick the alternative to show (keep the current one if still valid).
        if self._current_alt in self.alternatives:
            alt = self._current_alt
        elif self.alternatives:
            alt = self.alternatives[0]
        else:
            alt = None

        self._sync_selector_options()
        self._built = True

        if alt is None:
            with self.out:
                clear_output()
                display(HTML('<p style="color:#888">No alternatives defined.</p>'))
            return

        self._show_alt(alt)

    def get_all_outputs(self) -> OrderedDict:
        # Flush the visible alternative's live edits into the cache, then return
        # the full cache (all alternatives) so autosave/Results/export see
        # everything — not just the alternative currently on screen.
        self._flush_current_to_cache()
        alts = self.alternatives or list(self._value_cache.keys())
        return OrderedDict(
            {alt: OrderedDict(self._value_cache.get(alt, {})) for alt in alts}
        )

    def set_all_values(self, selected_values: dict, rating_scales: dict):
        if rating_scales:
            self.rating_scales = rating_scales
        # Cache plain data for every alternative; build no widgets here.
        self._value_cache = OrderedDict(
            {alt: OrderedDict(vals) for alt, vals in selected_values.items()}
        )
        self._built       = False
        self._current_alt = None
        self._current_rt  = None
        if not self.alternatives:
            self.alternatives = list(selected_values.keys())

    def saveTable(self, table_format='csv'):
        # Export reads the full cache (all alternatives), so it works even though
        # only one alternative has live widgets.
        data = self.get_all_outputs()
        final_df = pd.DataFrame(
            {alt.replace(' ', '_'): OrderedDict(vals) for alt, vals in data.items()}
        ).transpose()
        out_file = os.path.join(tmp_dir, f'ratingTables.{table_format}')
        if table_format == 'csv':
            final_df.to_csv(out_file)
        elif table_format == 'html':
            final_df.to_html(out_file)
        return out_file

    def exportRatings(self, b):
        csv_file = self.saveTable()
        filename = os.path.join(tmp_dir, 'ratingTables.zip')
        create_zip(filename, [csv_file])
        with self.downloadOut:
            clear_output()
            display(FileLink(filename))

    # ── private ───────────────────────────────────────────────────────────────

    def _sync_selector_options(self):
        self.altSelector.unobserve(self._on_alt_change, names='value')
        self.altSelector.options = self.alternatives
        if self._current_alt in self.alternatives:
            self.altSelector.value = self._current_alt
        elif self.alternatives:
            self.altSelector.value = self.alternatives[0]
        self.altSelector.observe(self._on_alt_change, names='value')

    def _flush_current_to_cache(self):
        if self._current_rt is not None and self._current_alt is not None:
            self._value_cache[self._current_alt] = OrderedDict(
                self._current_rt.get_all_outputs()
            )

    def _on_alt_change(self, change):
        if change['name'] == 'value' and change['new']:
            self._show_alt(change['new'])

    def _show_alt(self, alt):
        # Save the previously-shown alternative's edits before swapping.
        self._flush_current_to_cache()

        # Build fresh live widgets for THIS alternative only (~N_subcriteria
        # cells), populated from its cached values.
        rt = RatingTable(alt)
        rt.update(self.rating_scales)
        cached = self._value_cache.get(alt)
        if cached:
            rt.set_all_values(cached, self.rating_scales)

        self._current_alt = alt
        self._current_rt  = rt
        self._render_table(rt)

    def _render_table(self, rt):
        if not self.rating_scales:
            with self.out:
                clear_output()
                display(HTML('<p style="color:#888">No rating scales defined.</p>'))
            return

        subcriteria = list(self.rating_scales.keys())

        # Column 1: subcriteria names.
        lbl_header = widgets.HTML(
            f'<div style="{_HDR}text-align:left;min-width:220px;">Subcriteria</div>'
        )
        lbl_cells = [
            widgets.HTML(f'<div style="{_CELL}font-weight:500;">{s}</div>')
            for s in subcriteria
        ]
        label_col = widgets.VBox(
            [lbl_header] + lbl_cells,
            layout=widgets.Layout(flex='0 0 auto', min_width='220px'),
        )

        # Column 2: the selected alternative's rating cells (the only live
        # selector widgets on screen).
        val_header = widgets.HTML(
            f'<div style="{_HDR}min-width:220px;">{rt.alternative}</div>'
        )
        val_cells = []
        for sub in subcriteria:
            sel = rt.selectors.get(sub)
            if sel is not None:
                sel.description = ''
                sel.style       = {'description_width': '0px'}
                sel.layout      = widgets.Layout(width='98%', min_width='180px')
                sel.add_class('rt-cell')
                val_cells.append(sel)
            else:
                val_cells.append(
                    widgets.HTML(f'<div style="{_CELL}color:#aaa;">—</div>')
                )
        value_col = widgets.VBox(
            [val_header] + val_cells,
            layout=widgets.Layout(flex='1 1 auto', min_width='220px'),
        )

        # Display the container empty first, then attach the two columns — the
        # front-end registers the (childless) HBox cleanly, then receives the
        # ~N_subcriteria cell models and attaches them as they arrive.
        table_widget = widgets.HBox(
            [],
            layout=widgets.Layout(
                width='auto',
                border='1px solid #d0d0d0',
                border_radius='4px',
                overflow='hidden',
            ),
        )
        with self.out:
            clear_output()
            display(HTML(_TABLE_CSS))
            display(table_widget)
        table_widget.children = [label_col, value_col]
