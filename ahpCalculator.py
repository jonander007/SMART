#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/ahpCalculator.py
import ipywidgets as widgets
import plotly.graph_objects as go
from collections import OrderedDict
import pandas as pd
import math
import matplotlib.pyplot as plt
import os
import webview
from IPython.display import display, HTML, clear_output
from IPython.display import FileLink
from base64 import b64encode
from jinja2 import Environment, FileSystemLoader
from .titleAndHelp import TitleAndHelp
from .constants import text_fontdict, tmp_dir, tab_titles, write_html_config, plot_width
from .utilities import get_loading_bar
from .notificationBar import NotificationBar
from .ahp import Compose
from .combinedTree import CombinedTree
from .utilities import create_zip, validate_inputs, make_bar_fig, make_pie_fig, make_double_pie_fig, assign_colors_and_hatches
from .smtReport import generate_compare_objects

__CREATION_DATE__ = 'Tuesday Jul 09, 2024 20:33:56 CEST'
__LAST_MODIFIED__ = 'Thursday Nov 13, 2025 20:07:32 CET'

#    TODO: 
#           Add things to do here

TAB = 5
TAB_TITLE = tab_titles[TAB]

loading_bar = get_loading_bar()

# The criteria-weights chart is matplotlib: Jupyter renders it as an <img> at the
# figure's natural pixel size (figsize x dpi), and CSS only ever shrinks it to
# fit. Forcing width:100% makes it fill its container instead, so it ends up
# exactly plot_width wide — the same as the plotly charts below it.
_CRIT_CSS = """
<style>
.crit-plot img { width: 100% !important; height: auto !important; }
</style>
"""

# matplotlib hatch -> equivalent CSS, so the clickable legend swatches look like
# the wedges they refer to.
_HATCH_LINES = 'rgba(0,0,0,.6) 0 1.5px, transparent 1.5px 5px'
_HATCH_CSS = {
    '':   '',
    '/':  f'repeating-linear-gradient(45deg, {_HATCH_LINES})',
    '\\': f'repeating-linear-gradient(-45deg, {_HATCH_LINES})',
    '|':  f'repeating-linear-gradient(90deg, {_HATCH_LINES})',
    '-':  f'repeating-linear-gradient(0deg, {_HATCH_LINES})',
    '+':  (f'repeating-linear-gradient(0deg, {_HATCH_LINES}), '
           f'repeating-linear-gradient(90deg, {_HATCH_LINES})'),
    'x':  (f'repeating-linear-gradient(45deg, {_HATCH_LINES}), '
           f'repeating-linear-gradient(-45deg, {_HATCH_LINES})'),
    '.':  'radial-gradient(rgba(0,0,0,.6) 1px, transparent 1.2px)',
}


def _swatch_html(color_css, hatch):
    """A legend colour patch: base colour plus the wedge's hatch pattern."""
    pattern = _HATCH_CSS.get((hatch or '')[:1], '')
    layers = f'{pattern}, ' if pattern else ''
    return (
        f'<div style="width:34px;height:16px;border:1px solid #333;'
        f'background-image:{layers}linear-gradient({color_css},{color_css});'
        f'background-size:6px 6px, auto;"></div>'
    )

class AhpCalculator():
    def __init__(self, logger, tree=None, criteria_compares=None, alternatives_names=None, alternatives_compares=None):
        self.logger = logger
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Initializing')
        self.tree = tree
        self.criteria_compares = criteria_compares
        self.alternatives_names = alternatives_names
        self.alternatives_compares = alternatives_compares
        self.invalid = False
        self.critplot = None
        self.compose = Compose()
        self.alternatives_scores = {}
        self.title = TitleAndHelp('Results', 'docs/help_ahpCalculator.html')
        self.critlabel =  widgets.Label(
                    value = 'Criteria Weights',
                    style = dict(
                            font_weight='bold',
                        )
                    )
        # The criteria-weights chart is matplotlib: it renders as an <img> that
        # the browser stretches to the container, so it used to span the whole
        # tab while the plotly charts below sat at a fixed width. Cap it to the
        # same width so every chart in this tab lines up. Both come from
        # constants.plot_width — change that one number to resize them all.
        self.critplotsOut = widgets.Output(
            layout=widgets.Layout(width=f'{plot_width // 2}px')
        )
        self.critplotsOut.add_class('crit-plot')
        # What-if filter: untick a criterion/subcriterion to drop it from the
        # chart; the remaining weights are renormalised so they still add to
        # 100%. This only re-slices the weights already computed by the AHP —
        # it does NOT re-run the hierarchy, so it is a read-only what-if view.
        self._weights_df    = None
        self._crit_checks   = {}   # name -> Checkbox
        self._crit_parent   = {}   # subcriterion -> its criterion
        self._crit_labels   = {}   # name -> HTML widget showing the live %
        # The legend is no longer drawn inside the matplotlib image: it is built
        # from widgets so each entry can be ticked to show/hide its wedge.
        self.critLegendBox = widgets.VBox(
            [], layout=widgets.Layout(width=f'{plot_width // 2}px')
        )
        self.critRow = widgets.HBox(
            [self.critplotsOut, self.critLegendBox],
            layout=widgets.Layout(width=f'{plot_width}px', align_items='center'),
        )
        self.plotsOut = widgets.Output(
            layout=widgets.Layout(width=f'{plot_width}px')
        )
        self.downloadOut = widgets.Output()
        self.notif = NotificationBar()
        self.exportButton = widgets.Button(
            description='Export Figures',
            disabled=False,
            button_style='', # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Export Matrices and Figures',
            style={'description_width': 'initial'},
            )
        self.allWidgets = widgets.VBox([
                self.notif.widget,
                self.title.allWidgets,
                self.critlabel,
                self.critRow,
                self.plotsOut,
                self.exportButton,
                self.downloadOut
            ])
        self.exportButton.on_click(self.exportFigures)


    def update(self, tree_dict, criteria_compares_dict, alternatives_names, alternatives_compares_dict, criteria_colors):
        self.logger.log('info', f'Tab {TAB} - {TAB_TITLE}: Updating')
        with self.plotsOut:
            clear_output()
            display(loading_bar)
        self.invalid = validate_inputs(self.notif, tree_dict, criteria_compares_dict, alternatives_names, alternatives_compares_dict)
        if not self.invalid:
            # Update tree object
            self.tree = CombinedTree()
            self.tree.from_dict(tree_dict)
            #  self.criteria_compares = criteria_compares
            self.criteria_compares = generate_compare_objects(criteria_compares_dict)
            self.alternatives_names = alternatives_names[:-1]
            #  self.alternatives_compares = alternatives_compares
            if alternatives_names[-1] == 'Pairwise Comparison':
                self.alternatives_compares = generate_compare_objects(alternatives_compares_dict)
            else:
                self.alternatives_compares = generate_compare_objects(alternatives_compares_dict, is_rating_scale=True)
            self.compose = Compose()
            self.compose.add_comparisons(list(self.criteria_compares.values()) + list(self.alternatives_compares.values()))
            #  print(self.tree.get_hierarchy())
            self.compose.add_hierarchy(self.tree.get_hierarchy())
            for alternative in self.alternatives_names:
                self.alternatives_scores[alternative] = {}
                for criteria in self.alternatives_compares.keys():
                    self.alternatives_scores[alternative][criteria] = self.compose[criteria]['global_weights'][alternative]
                    #  self.alternatives_scores[alternative][criteria] = self.compose[criteria]['local_weights'][alternative]

                #  self.alternatives_scores[alternative][self.tree.root] = self.compose[self.tree.root]['target_weights'][alternative]


            data = {alternative: self.compose[self.tree.root]['target_weights'][alternative] for alternative in self.alternatives_names}
            self.ranking = OrderedDict(reversed(sorted(data.items(), key=lambda x:x[1])))
            self.plots = []
            self.labels = []

            df = self.get_criteria_weights()
            # Keep the unfiltered weights + colours so the what-if filter can
            # redraw the chart without recomputing the AHP.
            self._weights_df     = df
            self._criteria_colors = criteria_colors
            self._build_criteria_filters(df)
            # Double pie chart with criteria/subcriteria weights
            fig = make_double_pie_fig(df, criteria_colors)
            self.critplot = fig

            # Bar Plot with all alternatives
            alternatives_df = self.get_weighted_scores('global_weights')
            fig = make_bar_fig(alternatives_df, criteria_colors)
            self.plots.append(go.FigureWidget(fig))
            self.labels.append(
                    widgets.Label(
                        value = 'Global Ranking',
                        style = dict(
                                font_weight='bold',
                            )
                        )
                    )

            # Donut plots
            for alternative in self.ranking.keys():
                fig = make_pie_fig(alternatives_df, criteria_colors, title=alternative, is_scores=True)
                self.plots.append(go.FigureWidget(fig))
                self.labels.append(
                        widgets.Label(
                            value = alternative,
                            style = dict(
                                    font_weight='bold',
                                )
                            )
                        )

            with self.critplotsOut:
                clear_output()
                display(HTML(self._critplot_html(self.critplot)))
            with self.plotsOut:
                clear_output()
                display(widgets.VBox(
                    [val for pair in zip(self.labels,self.plots) for val in pair]
                    ))

    # ── What-if filter for the criteria-weights chart ─────────────────────────

    def _build_criteria_filters(self, df):
        """Build the clickable legend: one row per criterion / subcriterion.

        Each row is [checkbox] [colour+hatch swatch] [name (weight %)], in
        hierarchy order — the same content the matplotlib legend used to draw
        inside the image, but tickable.
        """
        level_cols = [c for c in df.columns if c.startswith('Level')]
        self._crit_checks = {}
        self._crit_parent = {}
        self._crit_labels = {}
        rows = [widgets.HTML(
            '<div style="font-weight:700;text-align:center;padding:6px 0;'
            'border-bottom:1px solid #ccc;margin-bottom:6px;">'
            'Criteria &amp; Subcriteria</div>'
        )]
        for _, r in df.iterrows():
            parent = None
            for i, col in enumerate(level_cols):
                name = r[col]
                if pd.isna(name):
                    continue
                if name not in self._crit_checks:
                    cb = widgets.Checkbox(
                        value=True, indent=False,
                        layout=widgets.Layout(width='24px', margin='0'),
                    )
                    cb.observe(self._on_criteria_filter_change, names='value')
                    self._crit_checks[name] = cb

                    match = self._criteria_colors[
                        self._criteria_colors['Criteria'] == name]
                    if len(match):
                        color_css = match['Color Plotly'].iloc[0]
                        hatch     = match['Hatches'].iloc[0]
                    else:
                        color_css, hatch = 'rgba(200,200,200,1)', ''
                    swatch = widgets.HTML(
                        _swatch_html(color_css, hatch),
                        layout=widgets.Layout(width='40px'),
                    )
                    label = widgets.HTML(layout=widgets.Layout(width='auto'))
                    self._crit_labels[name] = label

                    if parent is not None:
                        self._crit_parent[name] = parent
                    rows.append(widgets.HBox(
                        [cb, swatch, label],
                        layout=widgets.Layout(
                            align_items='center',
                            margin=f'0 0 0 {i * 22}px',   # indent subcriteria
                        ),
                    ))
                parent = name
        self.critLegendBox.children = rows

    def _refresh_legend(self, kept):
        """Update each legend row with the weight it has after redistribution."""
        level_cols = [c for c in self._weights_df.columns
                      if c.startswith('Level')]
        crit_col = level_cols[0]
        pct = {}
        if not kept.empty:
            for crit, grp in kept.groupby(crit_col, sort=False):
                pct[crit] = grp['Weight'].sum()
            for _, r in kept.iterrows():
                for col in level_cols[1:]:
                    if pd.notna(r[col]):
                        pct[r[col]] = r['Weight']
        for name, label in self._crit_labels.items():
            cb = self._crit_checks.get(name)
            if cb is not None and not cb.value:
                label.value = (f'<span style="color:#bbb;text-decoration:line-through">'
                               f'{name}</span>')
            elif name in pct:
                label.value = (f'<span>{name} '
                               f'<b>({pct[name] * 100:.2f}%)</b></span>')
            else:
                label.value = f'<span style="color:#bbb">{name}</span>'

    def _on_criteria_filter_change(self, change):
        # Unticking a criterion greys out its subcriteria: they are already
        # excluded by _apply_filter(), the disabled state just makes that visible.
        for sub, parent in self._crit_parent.items():
            pcb = self._crit_checks.get(parent)
            scb = self._crit_checks.get(sub)
            if pcb is not None and scb is not None:
                scb.disabled = not pcb.value
        self._redraw_criteria_plot()

    def _leaf_visible(self, row, level_cols):
        """True if none of this leaf's SUBcriteria levels has been unticked."""
        for col in level_cols[1:]:
            name = row[col]
            if pd.isna(name):
                continue
            cb = self._crit_checks.get(name)
            if cb is not None and not cb.value:
                return False
        return True

    def _apply_filter(self, df):
        """Redistribute the weights of whatever the user has hidden.

        Two different rules, per the analyst's mental model of the hierarchy:

          * hiding a SUBcriterion -> its weight is shared out among the
            remaining subcriteria of the SAME criterion, proportionally. The
            criterion keeps the exact weight it had (nothing leaks to its
            siblings).
          * hiding a CRITERION -> its weight is shared out among the remaining
            criteria, proportionally (each of them scales up, and so do their
            subcriteria).

        The two compose: normalise inside each criterion first (which preserves
        the criterion weights), then normalise across criteria.
        """
        level_cols = [c for c in df.columns if c.startswith('Level')]
        crit_col   = level_cols[0]
        kept_parts = []
        for crit, grp in df.groupby(crit_col, sort=False):
            cb = self._crit_checks.get(crit)
            if cb is not None and not cb.value:
                continue                       # criterion hidden -> drop it whole
            weight_of_criterion = grp['Weight'].sum()   # its ORIGINAL weight
            visible = grp[grp.apply(
                lambda r: self._leaf_visible(r, level_cols), axis=1)].copy()
            visible_sum = visible['Weight'].sum()
            if visible.empty or not math.isfinite(visible_sum) or visible_sum <= 0:
                continue                       # every subcriterion hidden
            # Scale the survivors back up to the criterion's own weight, so the
            # criterion's slice of the inner ring does not move.
            visible['Weight'] = visible['Weight'] * (weight_of_criterion / visible_sum)
            kept_parts.append(visible)

        if not kept_parts:
            return df.iloc[0:0]
        kept  = pd.concat(kept_parts)
        total = kept['Weight'].sum()
        if math.isfinite(total) and total > 0:
            # Only bites when a whole criterion is hidden; otherwise total == 1.
            kept['Weight'] = kept['Weight'] / total
        return kept

    def _redraw_criteria_plot(self):
        if self._weights_df is None:
            return
        kept = self._apply_filter(self._weights_df)
        self._refresh_legend(kept)

        with self.critplotsOut:
            clear_output()
            display(HTML(_CRIT_CSS))
            # Guard: an empty selection would make matplotlib raise
            # "Wedge sizes must be finite numbers".
            if kept.empty:
                display(HTML(
                    '<p style="color:#888;padding:12px">'
                    'Tick at least one criterion to draw the chart.</p>'
                ))
                return
            if self.critplot is not None:
                plt.close(self.critplot)      # free the previous figure
            # show_legend=True: draw the 2-column criteria list INSIDE the image
            # so it is part of the zoomable view and the downloaded PNG. The
            # tickable checkbox legend still lives beside the chart as the filter
            # control.
            self.critplot = make_double_pie_fig(
                kept, self._criteria_colors, show_legend=True,
                width_px=plot_width // 2,
            )
            display(HTML(self._critplot_html(self.critplot)))

    def get_criteria_weights(self):
        #  df = pd.DataFrame([], columns=['Criteria', 'Subcriteria', 'Weight'])
        depth = self.tree.treelib_tree.depth()
        leafs = list(self.tree.treelib_tree.filter_nodes(lambda n: n.is_leaf(self.tree.treelib_tree.identifier)))
        #  print(depth)
        weights = {}
        for level in reversed(range(1, depth)):
            #  print(level)
            nodes = self.tree.get_node_names(level=level)
            #  print(nodes)
            for node in nodes:
                #  print(node)
                if self.tree.get_treelib_node(node) not in leafs:
                    compare = self.compose._get_node(node)
                    #  print(compare.global_weights)
                    weights = weights | compare.global_weights
            #  print(weights)
        leaves = self.tree.treelib_tree.leaves()
        paths = []
        for leaf in leaves:
            path = self.tree.treelib_tree.rsearch(leaf.identifier)
            path_names = [self.tree.treelib_tree[node_id].tag for node_id in reversed(list(path)) if self.tree.treelib_tree[node_id].tag != self.tree.root]
            paths.append(path_names)
        df = pd.DataFrame(paths)
        df.columns = [f"Level{i+1}" for i in range(df.shape[1])]
        df['Weight'] = df.apply(lambda row: weights.get(row.dropna().iloc[-1], None), axis=1)
        df.to_csv('my_weights.csv')
        #  print(df)




        #  for criteria, compare in self.criteria_compares.items():
            #  print(compare.global_weights)
            #  if criteria is not self.tree.root:
                #  for subcriteria, weight in compare['global_weights'].items():
                    #  df.loc[len(df)] = {'Criteria': criteria, 'Subcriteria': subcriteria, 'Weight': weight}
        #  df.to_csv('criteria_weights.csv')
        return df
                
    def get_weighted_scores(self, weights='global_weights'):
        scores = {}
        for alternative in self.alternatives_names:
            scores[alternative] = {}
            for criteria in self.alternatives_compares.keys():
                scores[alternative][criteria] = self.compose[criteria][weights][alternative]
        final_df = pd.DataFrame(scores)
        final_df = final_df.transpose()
        final_df.reset_index(names='Alternatives', inplace=True)
        #  final_df.to_csv('final_df.csv')
        return final_df

    def saveAll(self, df_format='html', im_format='html'):
        file_dict = {}
        im_file = 'Criteria_Weights.png'
        im_file = os.path.join(tmp_dir, im_file)
        self.critplot.savefig(im_file, bbox_inches='tight')
        file_dict['Criteria_Weights'] = im_file
        for i, plot in enumerate(self.plots):
            im_file = '{}_Scores.{}'.format(self.labels[i].value, im_format)
            im_file = os.path.join(tmp_dir, im_file)
            if im_format == 'html':
                #  plot.data[0].write_hmtl(im_file)
                fig = go.Figure(plot.to_plotly_json())
                fig.write_html(im_file, full_html=False, config=write_html_config)
            else:
                plot.write_image(im_file)
            file_dict[self.labels[i].value] = im_file
        #  for weights in ['global_weights', 'target_weights']:
        for weights in ['global_weights', 'local_weights']:
            df = self.get_weighted_scores(weights)
            df_file = '{}.{}'.format(weights, df_format)
            df_file = os.path.join(tmp_dir, df_file)
            if df_format == 'csv':
                df.to_csv(df_file)
            else:
                df.to_html(df_file)
            file_dict[weights] = df_file
        return file_dict

    def _critplot_html(self, fig, dl_name='criteria_weights.png'):
        """Render the matplotlib criteria-weights figure to a high-res PNG shown
        inside a zoomable, pannable, downloadable container.

        Zoom buttons use inline onclick handlers so they work even where Voila
        strips standalone <script> tags; ctrl+wheel zoom and drag-pan are added
        as progressive enhancements. The 'Download PNG' link is a data: URL, so
        the exact chart on screen can be saved with one click.
        """
        import io
        buf = io.BytesIO()
        # Use the figure's OWN dpi (make_double_pie_fig already sets it to
        # plot_width/side, i.e. the resolution the chart rendered at before this
        # change). A fixed dpi=200 produced a ~3000px PNG regenerated on every
        # what-if filter click — that was the slowdown. Cap keeps it crisp but
        # light; zoom still works on this base image.
        dpi = fig.get_dpi() or 120
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        b64 = b64encode(buf.read()).decode()
        buf.close()

        uid  = f'crit{id(fig)}'
        im   = f'im_{uid}'
        vp   = f'vp_{uid}'
        href = f'data:image/png;base64,{b64}'
        zin = (f"var i=document.getElementById('{im}');"
               f"var s=Math.min(8,(parseFloat(i.dataset.s)||1)*1.25);"
               f"i.dataset.s=s;i.style.transform='scale('+s+')';")
        zout = (f"var i=document.getElementById('{im}');"
                f"var s=Math.max(0.3,(parseFloat(i.dataset.s)||1)*0.8);"
                f"i.dataset.s=s;i.style.transform='scale('+s+')';")
        zres = (f"var i=document.getElementById('{im}');i.dataset.s=1;"
                f"i.style.transform='scale(1)';"
                f"var v=document.getElementById('{vp}');v.scrollTop=0;v.scrollLeft=0;")
        return f"""
<style>
.critwrap {{ border:1px solid #ddd; border-radius:6px; margin-bottom:8px; }}
.crit-tb {{ display:flex; gap:6px; align-items:center; padding:6px 8px;
            background:#f7f7f7; border-bottom:1px solid #eee; }}
.crit-tb button, .crit-tb a {{ font-size:13px; padding:4px 10px; border:1px solid #ccc;
            border-radius:4px; background:#fff; color:#333; cursor:pointer; text-decoration:none; }}
.crit-tb button:hover, .crit-tb a:hover {{ background:#eef2ff; }}
.crit-tb .sp {{ flex:1; }}
.crit-vp {{ overflow:auto; max-height:720px; cursor:grab; }}
.crit-vp img {{ max-width:100%; transform-origin:top left; display:block; }}
</style>
<div class="critwrap">
  <div class="crit-tb">
    <button title="Zoom in"  onclick="{zin}">&#10133;</button>
    <button title="Zoom out" onclick="{zout}">&#10134;</button>
    <button title="Reset"    onclick="{zres}">Reset</button>
    <span class="sp"></span>
    <a download="{dl_name}" href="{href}">&#11015; Download PNG</a>
  </div>
  <div class="crit-vp" id="{vp}">
    <img id="{im}" src="{href}" data-s="1"/>
  </div>
</div>
<script>
(function(){{
  var vp=document.getElementById('{vp}'); if(!vp) return;
  var im=document.getElementById('{im}');
  vp.addEventListener('wheel',function(e){{ if(!e.ctrlKey) return; e.preventDefault();
    var s=(parseFloat(im.dataset.s)||1)*(e.deltaY<0?1.1:0.9);
    s=Math.max(0.3,Math.min(8,s)); im.dataset.s=s; im.style.transform='scale('+s+')'; }},{{passive:false}});
  var d=false,sx,sy,sl,st;
  vp.addEventListener('mousedown',function(e){{d=true;sx=e.clientX;sy=e.clientY;
    sl=vp.scrollLeft;st=vp.scrollTop;vp.style.cursor='grabbing';}});
  window.addEventListener('mouseup',function(){{d=false;vp.style.cursor='grab';}});
  vp.addEventListener('mousemove',function(e){{ if(!d)return;
    vp.scrollLeft=sl-(e.clientX-sx); vp.scrollTop=st-(e.clientY-sy); }});
}})();
</script>
"""

    def exportFigures(self, b):
        with self.downloadOut:
            clear_output()
            self.notif.info('Preparing download...')
        file_dict = self.saveAll()
        file_list = list(file_dict.values())
        filename = 'scores.zip'
        filename = os.path.join(tmp_dir, filename)
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

