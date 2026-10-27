#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ipywidgets as widgets
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import math
import os
import webview
from IPython.display import display, HTML, clear_output
from IPython.display import FileLink
from .titleAndHelp import TitleAndHelp
from .constants import text_fontdict, tmp_dir, tab_titles, write_html_config, section_label_style
from .utilities import get_loading_bar, decode_tuples, encode_tuples, create_zip

__CREATION_DATE__ = 'Sunday May 31, 2026'
__LAST_MODIFIED__  = 'Sunday May 31, 2026'

TAB = 8
TAB_TITLE = 'Compare Results'

loading_bar = get_loading_bar()

COLORS = ["#636EFA","#EF553B","#00CC96","#AB63FA","#FFA15A",
          "#19D3F3","#FF6692","#B6E880","#FF97FF","#FECB52"]

# ─────────────────────────────────────────────────────────────────────────────
# MATH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _geom_mean(vals):
    vals = [v for v in vals if v > 0 and math.isfinite(v)]
    if not vals:
        return 0.0
    return math.exp(sum(math.log(v) for v in vals) / len(vals))

def _arith_mean(vals):
    vals = [v for v in vals if math.isfinite(v)]
    return sum(vals) / len(vals) if vals else 0.0

def _std_dev(vals, mean):
    vals = [v for v in vals if math.isfinite(v)]
    if len(vals) < 2:
        return 0.0
    return math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))


# ─────────────────────────────────────────────────────────────────────────────
# SMT PARSING
# ─────────────────────────────────────────────────────────────────────────────

def _load_smt(filepath):
    """Load and decode a .smt file, return the data dict."""
    with open(filepath, 'r', encoding='utf-8') as f:
        encoded = json.load(f)
    return decode_tuples(encoded)


def _extract_pairs(data):
    """Return dict  key -> {block, pstr, val}  from Criteria Comparison section."""
    cc = data.get('Criteria Comparison', {}).get('Criteria Comparison', {})
    pairs = {}
    for block, pair_dict in cc.items():
        for pstr, val in pair_dict.items():
            key = f"{block}|||{pstr}"
            pairs[key] = {'block': block, 'pstr': pstr, 'val': float(val)}
    return pairs


def _extract_final_scores(data):
    """
    Try to read pre-computed final scores from the smt if present.
    Returns dict  alternative -> score  or empty dict.
    """
    # SMART stores this under Results > target_weights if previously calculated
    results = data.get('Results', {})
    target = results.get('target_weights', {})
    return {k: float(v) for k, v in target.items()} if target else {}


def _short_pair(pstr):
    """Convert  ('A', 'B')  to  A / B  for display."""
    import re
    m = re.match(r"\('(.+?)',\s*'(.+?)'\)", str(pstr))
    return f"{m.group(1)} / {m.group(2)}" if m else str(pstr)


# ─────────────────────────────────────────────────────────────────────────────
# AGGREGATION CORE
# ─────────────────────────────────────────────────────────────────────────────

def aggregate_experts(expert_list, method='geom', threshold=2.0):
    """
    Parameters
    ----------
    expert_list : list of dict  {name, filepath, data}
    method      : 'geom' (AIJ geometric mean) or 'arith' (AIP arithmetic mean)
    threshold   : z-score cutoff for outlier detection

    Returns
    -------
    dict with keys:
      aggregated  - list of dicts per pair
      outliers    - list of dicts
      all_same    - bool
    """
    mean_fn = _geom_mean if method == 'geom' else _arith_mean

    # Collect all pair values per expert
    pair_map = {}
    for ei, exp in enumerate(expert_list):
        for key, info in _extract_pairs(exp['data']).items():
            if key not in pair_map:
                pair_map[key] = {'block': info['block'], 'pstr': info['pstr'], 'entries': []}
            pair_map[key]['entries'].append({'ei': ei, 'name': exp['name'], 'val': info['val']})

    all_same = True
    aggregated = []
    outliers   = []

    for key, d in pair_map.items():
        entries = d['entries']
        vals    = [e['val'] for e in entries if e['val'] > 0 and math.isfinite(e['val'])]
        if not vals:
            continue

        am = _arith_mean(vals)
        s  = _std_dev(vals, am)
        if s > 1e-6:
            all_same = False

        flagged = set()
        for e in entries:
            z = abs(e['val'] - am) / s if s > 0 else 0.0
            if z > threshold:
                flagged.add(e['ei'])
                outliers.append({**e, 'block': d['block'], 'pstr': d['pstr'],
                                  'mean': am, 'std': s, 'z': z})

        clean_vals = [e['val'] for e in entries
                      if e['ei'] not in flagged and e['val'] > 0 and math.isfinite(e['val'])]
        raw_mean   = mean_fn(vals)
        clean_mean = mean_fn(clean_vals) if clean_vals else raw_mean
        cv         = (s / am * 100) if am > 0 else 0.0
        max_z      = max((abs(v - am) / s if s > 0 else 0.0) for v in vals)

        aggregated.append({
            'block':      d['block'],
            'pstr':       d['pstr'],
            'entries':    entries,
            'vals':       vals,
            'raw_mean':   raw_mean,
            'clean_mean': clean_mean,
            'n_out':      len(flagged),
            'n':          len(vals),
            'std':        s,
            'cv':         cv,
            'max_z':      max_z,
            'min':        min(vals),
            'max':        max(vals),
        })

    return {'aggregated': aggregated, 'outliers': outliers, 'all_same': all_same}


# ─────────────────────────────────────────────────────────────────────────────
# PLOTTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_criteria_weights_fig(aggregated, expert_list):
    """Grouped bar: one group per criterion pair, one bar per expert + aggregated."""
    labels  = [_short_pair(a['pstr']) for a in aggregated]
    n_pairs = len(labels)
    if n_pairs == 0:
        return go.Figure()

    fig = go.Figure()
    for ei, exp in enumerate(expert_list):
        y = []
        for a in aggregated:
            entry = next((e for e in a['entries'] if e['ei'] == ei), None)
            y.append(entry['val'] if entry else None)
        fig.add_trace(go.Bar(
            name=exp['name'],
            x=labels,
            y=y,
            marker_color=COLORS[ei % len(COLORS)],
            opacity=0.75,
        ))

    # Aggregated (clean mean) as a scatter overlay
    fig.add_trace(go.Scatter(
        name='Aggregated (clean mean)',
        x=labels,
        y=[a['clean_mean'] for a in aggregated],
        mode='markers+lines',
        marker=dict(size=8, symbol='diamond', color='white',
                    line=dict(color='black', width=2)),
        line=dict(color='rgba(0,0,0,0.4)', dash='dot'),
    ))

    fig.update_layout(
        barmode='group',
        title='Pairwise judgments per expert vs. aggregated',
        xaxis=dict(title='Criterion pair', tickangle=-40,
                   tickfont=text_fontdict),
        yaxis=dict(title='Saaty value'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=520,
        margin=dict(b=160),
        font=text_fontdict,
    )
    return fig


def _make_divergence_fig(aggregated):
    """Horizontal bar of CV% sorted descending."""
    sorted_agg = sorted(aggregated, key=lambda a: a['cv'], reverse=True)[:30]
    labels = [_short_pair(a['pstr']) for a in sorted_agg]
    cvs    = [a['cv'] for a in sorted_agg]
    colors = ['#ef4444' if c > 50 else '#f59e0b' if c > 20 else '#22c55e' for c in cvs]

    fig = go.Figure(go.Bar(
        x=cvs,
        y=labels,
        orientation='h',
        marker_color=colors,
        text=[f"{c:.1f}%" for c in cvs],
        textposition='outside',
    ))
    fig.update_layout(
        title='Divergence between experts (CV%) — top 30 pairs',
        xaxis=dict(title='Coefficient of Variation (%)'),
        yaxis=dict(autorange='reversed'),
        height=max(400, 22 * len(labels)),
        margin=dict(l=220, r=60),
        font=text_fontdict,
    )
    return fig


def _make_outlier_fig(outliers, expert_list):
    """Scatter: each outlier as a point coloured by expert."""
    if not outliers:
        return go.Figure().update_layout(
            title='No outliers detected',
            height=300,
            font=text_fontdict,
        )
    df = pd.DataFrame(outliers)
    df['pair_label'] = df['pstr'].apply(_short_pair)
    fig = go.Figure()
    for i, expert_name in enumerate(df['name'].unique()):
        sub = df[df['name'] == expert_name]
        fig.add_trace(go.Scatter(
            x=sub['pair_label'], y=sub['val'],
            mode='markers',
            name=expert_name,
            marker=dict(
                size=sub['z'].clip(lower=2) * 8,
                color=COLORS[i % len(COLORS)],
                opacity=0.8,
            ),
            customdata=sub[['z','mean','std']].values,
            hovertemplate=(
                '<b>%{x}</b><br>'
                'Value: %{y:.4f}<br>'
                'Z-score: %{customdata[0]:.2f}<br>'
                'Mean: %{customdata[1]:.4f}<br>'
                'Std: %{customdata[2]:.4f}<extra></extra>'
            ),
        ))
    fig.update_layout(
        title='Outlier values per pair (bubble size = Z-score)',
        xaxis_title='Criterion pair', yaxis_title='Expert value',
    )
    fig.update_layout(
        xaxis_tickangle=-40,
        height=480,
        margin=dict(b=160),
        font=text_fontdict,
    )
    return fig


def _make_scores_comparison_fig(expert_list):
    """
    If experts have pre-computed final scores (Results > target_weights),
    show a grouped bar chart comparing alternative rankings.
    """
    traces = []
    for ei, exp in enumerate(expert_list):
        scores = _extract_final_scores(exp['data'])
        if not scores:
            continue
        alts = list(scores.keys())
        vals = list(scores.values())
        traces.append(go.Bar(
            name=exp['name'],
            x=alts,
            y=vals,
            marker_color=COLORS[ei % len(COLORS)],
            opacity=0.8,
        ))
    if not traces:
        return None
    fig = go.Figure(data=traces)
    fig.update_layout(
        barmode='group',
        title='Final alternative scores per expert (from saved Results)',
        xaxis=dict(title='Alternative'),
        yaxis=dict(title='Score'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=460,
        font=text_fontdict,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def _build_aggregated_smt(base_data, aggregated, expert_list, method, threshold):
    """Return a new smt dict with clean aggregated pairwise values."""
    import copy
    out = copy.deepcopy(base_data)
    cc = out.setdefault('Criteria Comparison', {}).setdefault('Criteria Comparison', {})
    for a in aggregated:
        cc.setdefault(a['block'], {})[a['pstr']] = a['clean_mean']
    gen = out.setdefault('General', {})
    gen['Analyst']     = f"Aggregated ({method}, thr={threshold}σ, n={len(expert_list)})"
    gen['Date']        = pd.Timestamp.now().strftime('%d-%m-%Y')
    gen['Description'] = gen.get('Description', '') + ' [aggregated]'
    return out


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TAB CLASS
# ─────────────────────────────────────────────────────────────────────────────

class ExpertAggregator():
    """
    Tab 7 — Compare Results
    Loads multiple .smt files, aggregates pairwise judgments (AIJ/AIP),
    detects outliers, and displays comparative charts.
    """

    def __init__(self, logger):
        self.logger = logger
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Initializing')

        self.expert_list = []   # list of {name, filepath, data}
        self.result      = None

        # ── Title ─────────────────────────────────────────────────────────
        self.title = TitleAndHelp('Compare Results', 'docs/help_ahpCalculator.html')

        # ── File upload button ────────────────────────────────────────────
        self.addFileBtn = widgets.Button(
            description='Add .smt files',
            button_style='info',
            icon='plus',
            tooltip='Select one or more .smt expert files',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='180px'),
        )

        self.clearBtn = widgets.Button(
            description='Clear all',
            button_style='warning',
            icon='trash',
            tooltip='Remove all loaded files',
            layout=widgets.Layout(width='120px'),
        )

        self.fileListOut = widgets.Output()

        # ── Method selector ───────────────────────────────────────────────
        self.methodToggle = widgets.ToggleButtons(
            options=[('AIJ — Geometric mean (recommended)', 'geom'),
                     ('AIP — Arithmetic mean', 'arith')],
            value='geom',
            description='Method:',
            style={'description_width': 'initial', 'button_width': '280px'},
        )

        # ── Threshold slider ──────────────────────────────────────────────
        self.thrSlider = widgets.FloatSlider(
            value=2.0, min=1.0, max=3.0, step=0.25,
            description='Outlier threshold (σ):',
            readout_format='.2f',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='480px'),
        )

        # ── Run button ────────────────────────────────────────────────────
        self.runBtn = widgets.Button(
            description='Run aggregation',
            button_style='success',
            icon='play',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='200px'),
        )

        # ── Output areas ──────────────────────────────────────────────────
        self.metricsOut  = widgets.Output()
        self.plotsOut    = widgets.Output()
        self.downloadOut = widgets.Output()
        self.errorOut    = widgets.Output()

        # ── Export buttons ────────────────────────────────────────────────
        self.exportCsvBtn = widgets.Button(
            description='Export CSV',
            button_style='',
            icon='download',
            disabled=True,
            layout=widgets.Layout(width='150px'),
        )
        self.exportSmtBtn = widgets.Button(
            description='Export .smt',
            button_style='',
            icon='download',
            disabled=True,
            layout=widgets.Layout(width='150px'),
        )

        # ── Alert label ───────────────────────────────────────────────────
        self.alertLabel = widgets.HTML(value='')

        # ── Layout ────────────────────────────────────────────────────────
        self.allWidgets = widgets.VBox([
            self.title.allWidgets,
            widgets.HBox([self.addFileBtn, self.clearBtn]),
            self.fileListOut,
            widgets.HBox([self.methodToggle]),
            self.thrSlider,
            widgets.HBox([self.runBtn, self.exportCsvBtn, self.exportSmtBtn]),
            self.alertLabel,
            self.metricsOut,
            self.plotsOut,
            self.downloadOut,
            self.errorOut,
        ])

        # ── Wire events ───────────────────────────────────────────────────
        self.addFileBtn.on_click(self._on_add_files)
        self.clearBtn.on_click(self._on_clear)
        self.runBtn.on_click(self._on_run)
        self.exportCsvBtn.on_click(self._on_export_csv)
        self.exportSmtBtn.on_click(self._on_export_smt)

    # ── File management ───────────────────────────────────────────────────

    def _on_add_files(self, _b):
        active = webview.active_window()
        result = active.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=('SMART Files (*.smt;*.json)', 'All files (*.*)'),
        )
        if not result:
            return
        for filepath in result:
            try:
                data = _load_smt(filepath)
                name = os.path.splitext(os.path.basename(filepath))[0]
                analyst = data.get('General', {}).get('Analyst', '')
                if analyst and len(analyst) < 25:
                    name = analyst
                self.expert_list.append({'name': name, 'filepath': filepath, 'data': data})
                self.logger.log('info', f'Loaded expert file: {filepath}')
            except Exception as e:
                self.logger.log('error', f'Could not load {filepath}: {e}')
                with self.errorOut:
                    clear_output()
                    print(f'Error loading {filepath}: {e}')
        self._render_file_list()

    def _on_clear(self, _b):
        self.expert_list = []
        self.result = None
        self._render_file_list()
        with self.metricsOut:
            clear_output()
        with self.plotsOut:
            clear_output()
        with self.downloadOut:
            clear_output()
        self.alertLabel.value = ''
        self.exportCsvBtn.disabled = True
        self.exportSmtBtn.disabled = True

    def _render_file_list(self):
        with self.fileListOut:
            clear_output()
            if not self.expert_list:
                print('No files loaded.')
                return
            items = ''.join(
                f'<li style="margin:2px 0"><b style="color:{COLORS[i % len(COLORS)]}">'
                f'●</b>&nbsp;{e["name"]}&nbsp;'
                f'<span style="color:#888;font-size:11px">({e["filepath"]})</span></li>'
                for i, e in enumerate(self.expert_list)
            )
            display(HTML(f'<ul style="margin:4px 0;padding-left:16px">{items}</ul>'))

    # ── Run ───────────────────────────────────────────────────────────────

    def _on_run(self, _b):
        with self.errorOut:
            clear_output()
        if len(self.expert_list) < 2:
            with self.errorOut:
                print('Load at least 2 .smt files to compare.')
            return

        with self.plotsOut:
            clear_output()
            display(loading_bar)

        method    = self.methodToggle.value
        threshold = self.thrSlider.value
        self.result = aggregate_experts(self.expert_list, method=method, threshold=threshold)
        self.result['method']    = method
        self.result['threshold'] = threshold

        self._render_metrics()
        self._render_plots()
        self.exportCsvBtn.disabled = False
        self.exportSmtBtn.disabled = False

        if self.result['all_same']:
            self.alertLabel.value = (
                '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;'
                'padding:8px 12px;margin:6px 0;font-size:13px;">'
                '⚠ All files appear to have identical values — they may be copies of the same questionnaire.'
                '</div>'
            )
        else:
            self.alertLabel.value = ''

    # ── Render metrics ────────────────────────────────────────────────────

    def _render_metrics(self):
        agg = self.result['aggregated']
        out = self.result['outliers']
        n_changed = sum(1 for a in agg if abs(a['raw_mean'] - a['clean_mean']) > 1e-4)
        max_cv    = max((a['cv'] for a in agg), default=0)

        cards = [
            ('Experts loaded',      len(self.expert_list)),
            ('Pairs analysed',      len(agg)),
            ('Outliers detected',   len(out)),
            ('Pairs adjusted',      n_changed),
            ('Max divergence (CV)', f'{max_cv:.1f}%'),
        ]
        html = '<div style="display:flex;gap:12px;flex-wrap:wrap;margin:12px 0;">'
        for label, value in cards:
            html += (
                f'<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;'
                f'padding:12px 18px;min-width:130px;">'
                f'<div style="font-size:22px;font-weight:700">{value}</div>'
                f'<div style="font-size:12px;color:#6c757d;margin-top:3px">{label}</div>'
                f'</div>'
            )
        html += '</div>'
        with self.metricsOut:
            clear_output()
            display(HTML(html))

    # ── Render plots ──────────────────────────────────────────────────────

    def _render_plots(self):
        agg          = self.result['aggregated']
        outliers     = self.result['outliers']
        expert_list  = self.expert_list

        fig_comp   = go.FigureWidget(_make_criteria_weights_fig(agg, expert_list))
        fig_div    = go.FigureWidget(_make_divergence_fig(agg))
        fig_out    = go.FigureWidget(_make_outlier_fig(outliers, expert_list))
        fig_scores = _make_scores_comparison_fig(expert_list)

        # Summary table
        rows = ''
        for a in agg:
            diff = a['clean_mean'] - a['raw_mean']
            diff_str = (f'<span style="color:{"green" if diff>0 else "red"}">'
                        f'{"+" if diff>0 else ""}{diff:.4f}</span>'
                        if abs(diff) > 1e-4 else '—')
            badge = (f'<span style="background:#fff3cd;padding:1px 6px;border-radius:4px;'
                     f'font-size:11px">{a["n_out"]} excl.</span>'
                     if a['n_out'] > 0
                     else '<span style="background:#d4edda;padding:1px 6px;border-radius:4px;font-size:11px">ok</span>')
            rows += (
                f'<tr>'
                f'<td style="font-size:12px;color:#666">{a["block"]}</td>'
                f'<td style="font-size:12px">{_short_pair(a["pstr"])}</td>'
                f'<td style="font-family:monospace">{a["raw_mean"]:.4f}</td>'
                f'<td>{badge}</td>'
                f'<td style="font-family:monospace"><b>{a["clean_mean"]:.4f}</b></td>'
                f'<td style="font-size:12px">{diff_str}</td>'
                f'<td style="font-family:monospace">{a["cv"]:.1f}%</td>'
                f'</tr>'
            )

        table_html = (
            '<div style="max-height:360px;overflow-y:auto;margin:12px 0;">'
            '<table style="width:100%;border-collapse:collapse;font-size:13px">'
            '<thead><tr style="position:sticky;top:0;background:#fff;border-bottom:2px solid #dee2e6">'
            '<th style="text-align:left;padding:6px 8px">Block</th>'
            '<th style="text-align:left;padding:6px 8px">Pair</th>'
            '<th style="padding:6px 8px">Raw mean</th>'
            '<th style="padding:6px 8px">Excluded</th>'
            '<th style="padding:6px 8px">Clean mean</th>'
            '<th style="padding:6px 8px">Δ</th>'
            '<th style="padding:6px 8px">CV%</th>'
            '</tr></thead>'
            f'<tbody>{rows}</tbody>'
            '</table></div>'
        )

        widgets_list = [
            widgets.Label('Pairwise judgments comparison', style=dict(font_weight='bold', font_size='16px')),
            fig_comp,
            widgets.Label('Divergence between experts', style=dict(font_weight='bold', font_size='16px')),
            fig_div,
            widgets.Label('Outlier values', style=dict(font_weight='bold', font_size='16px')),
            fig_out,
            widgets.Label('Aggregated values table', style=dict(font_weight='bold', font_size='16px')),
            widgets.HTML(table_html),
        ]
        if fig_scores is not None:
            widgets_list.insert(0, go.FigureWidget(fig_scores))
            widgets_list.insert(0, widgets.Label(
                'Alternative scores comparison (from saved Results)',
                style=dict(font_weight='bold', font_size='16px')
            ))

        with self.plotsOut:
            clear_output()
            display(widgets.VBox(widgets_list))

    # ── Exports ───────────────────────────────────────────────────────────

    def _on_export_csv(self, _b):
        if not self.result:
            return
        agg = self.result['aggregated']
        n_exp = len(self.expert_list)
        exp_names = [e['name'] for e in self.expert_list]

        rows = []
        for a in agg:
            row = {
                'Block':       a['block'],
                'Pair':        _short_pair(a['pstr']),
                'Raw_mean':    round(a['raw_mean'], 6),
                'N_excluded':  a['n_out'],
                'Clean_mean':  round(a['clean_mean'], 6),
                'Delta':       round(a['clean_mean'] - a['raw_mean'], 6),
                'CV_pct':      round(a['cv'], 2),
                'Method':      self.result['method'],
                'Threshold_sigma': self.result['threshold'],
            }
            for ei, name in enumerate(exp_names):
                entry = next((e for e in a['entries'] if e['ei'] == ei), None)
                row[name] = round(entry['val'], 6) if entry else ''
            rows.append(row)

        df = pd.DataFrame(rows)
        csv_path = os.path.join(tmp_dir, 'ahp_aggregation.csv')
        df.to_csv(csv_path, index=False)
        with self.downloadOut:
            clear_output()
            display(FileLink(csv_path))
        self.logger.log('info', f'Exported aggregation CSV to {csv_path}')

    def _on_export_smt(self, _b):
        if not self.result or not self.expert_list:
            return
        base_data = self.expert_list[0]['data']
        out_data  = _build_aggregated_smt(
            base_data,
            self.result['aggregated'],
            self.expert_list,
            self.result['method'],
            self.result['threshold'],
        )
        smt_path = os.path.join(tmp_dir, 'aggregated.smt')
        with open(smt_path, 'w', encoding='utf-8') as f:
            json.dump(encode_tuples(out_data), f, indent=2)
        with self.downloadOut:
            clear_output()
            display(FileLink(smt_path))
        self.logger.log('info', f'Exported aggregated .smt to {smt_path}')

    def update(self):
        """
        Called by tab_change when the user navigates to this tab.
        If run-idom-smart.py queued files via compare_paths.json, load them now.
        """
        paths_file = os.path.join(tmp_dir, 'compare_paths.json')
        if not os.path.isfile(paths_file):
            return
        try:
            with open(paths_file, 'r') as f:
                paths = json.load(f)
            os.remove(paths_file)   # consume once
            if not paths:
                return
            added = 0
            for filepath in paths:
                try:
                    data = _load_smt(filepath)
                    name = os.path.splitext(os.path.basename(filepath))[0]
                    analyst = data.get('General', {}).get('Analyst', '')
                    if analyst and len(analyst) < 25:
                        name = analyst
                    self.expert_list.append({'name': name, 'filepath': filepath, 'data': data})
                    added += 1
                    self.logger.log('info', f'Compare Results: loaded {filepath}')
                except Exception as e:
                    self.logger.log('error', f'Compare Results: could not load {filepath}: {e}')
            if added:
                self._render_file_list()
                with self.errorOut:
                    clear_output()
        except Exception as e:
            self.logger.log('error', f'Compare Results: failed reading paths file: {e}')

    # ── get_all_outputs / set_all_values (required by Smart.save_widget_state) ──


    def get_all_outputs(self):
        """Return serialisable state — nothing to persist for this tab."""
        return {}

    def set_all_values(self, data):
        """Restore state from saved file — nothing to restore for this tab."""
        pass
