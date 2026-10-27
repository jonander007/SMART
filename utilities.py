#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /home/cgt/03_PROJECTS/IDOM-SMART/idom-smart/scripts/utilities.py
import zipfile
import os, glob
from ipywidgets import Image
import numpy as np
import base64
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import webview
import pandas as pd
from cmcrameri import cm
from .constants import tmp_dir, default_goals, default_criteria, default_subcriteria, FILES_TO_CLEAN, mpl_fontdict, text_fontdict, figtitle_fontdict, axtitle_fontdict, axtick_fontdict, legend_fontdict, error_template, COLOR_SCALES, font_size
from .combinedTree import CombinedTree
from .scicolorscales import lapaz, berlin
__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Tuesday Jul 09, 2024 12:26:54 CEST'
__VERSION__ = '1.0.1'
__LAST_MODIFIED__ = 'Thursday Nov 13, 2025 20:39:24 CET'

#    TODO: 
#           Add things to do here

# set path for images
cwd = os.getcwd().split(os.sep)[-1]
if cwd == 'tests':
    imgpath = '../templates/images/'
else:
    imgpath = 'templates/images/'



# Rendered width, in pixels, of the full-bleed chart containers in the report.
# Used to work out how many legend entries fit per row. Defined here rather
# than in constants.py so that report styling never requires editing a module
# shared with the rest of the application.
REPORT_CHART_WIDTH = 1150


# RESULTS TAB
## Bar Plot
def make_bar_fig(df, colors_df, hatch_color='black'):
    traces =[]
    colors = dict(colors_df[['Criteria', 'Color Plotly']].values)
    hatches = dict(colors_df[['Criteria', 'Hatches']].values)
    subcriteria_columns = df.columns[1:]
    sizes = []
    for subcriteria in subcriteria_columns:
        # Top-level criteria that have no subcriteria are assigned an empty
        # hatch pattern. Guard against it: hatch[0] raised IndexError and
        # 16/len(hatch) raised ZeroDivisionError for those columns.
        hatch = hatches.get(subcriteria, '') or ''
        pattern_shape = hatch[0] if hatch else ''
        pattern_size = 16 / len(hatch) if hatch else 16
        trace = go.Bar(
                x=df['Alternatives'],
                y=df[subcriteria],
                name=subcriteria,
                textfont=text_fontdict,
                marker_color=colors.get(subcriteria, None),
                marker_pattern_shape=pattern_shape,
                marker_pattern_size=pattern_size
                )
        traces.append(trace)
        sizes.append(pattern_size)
    fig = go.Figure(data=traces)
    # Total score on top of each stack: with ~20 stacked segments the overall
    # ranking is otherwise hard to read off the axis.
    totals = df[list(subcriteria_columns)].sum(axis=1)
    fig.add_trace(go.Scatter(
        x=df['Alternatives'],
        y=totals,
        text=[f'{t:.3f}' for t in totals],
        mode='text',
        textposition='top center',
        textfont=dict(family='Courier New', size=12, color='rgba(0,0,0,0.75)'),
        showlegend=False,
        hoverinfo='skip',
        cliponaxis=False,
        ))
    # The legend previously sat on the right at full body font size. With ~20
    # subcriteria it swallowed most of the canvas and got clipped, so it now
    # runs horizontally underneath the plot at a smaller size, and the figure
    # is left responsive (width=None) so it can fill the page width.
    n_series = len(subcriteria_columns)
    # Scale the fonts for this figure only, leaving the shared constants
    # untouched (the globals are sized for a 1000px canvas).
    def _font(base, size):
        f = dict(base)
        f['size'] = size
        return f
    bar_title_font = _font(figtitle_fontdict, 20)
    bar_axtitle_font = _font(axtitle_fontdict, 15)
    bar_tick_font = _font(axtick_fontdict, 12)
    legend_font = _font(legend_fontdict, 12)
    # Height budget, in pixels. Everything below is derived so the legend can
    # never land on top of the x tick labels or the axis title, however long
    # the subcriteria names are.
    #
    # Legend rows: estimate how many entries fit per row from the longest
    # label. Courier New at 12px is ~7.2px per character, plus ~55px for the
    # colour swatch and padding. REPORT_CHART_WIDTH is the rendered width of
    # the full-bleed container the report puts these charts in.
    longest = max((len(str(c)) for c in subcriteria_columns), default=10)
    entry_px = longest * 7.2 + 55
    per_row = max(1, int(REPORT_CHART_WIDTH / entry_px))
    legend_rows = -(-n_series // per_row)
    legend_px = legend_rows * 24 + 20
    # Space for the rotated category labels plus the 'Alternatives' title.
    # Derived from the longest alternative name: at -30 degrees its vertical
    # extent is len * 7.2 * sin(30) = len * 3.6 px, and the axis title plus
    # padding needs another ~60px.
    longest_alt = max((len(str(a)) for a in df['Alternatives']), default=10)
    xaxis_px = int(min(220, max(95, longest_alt * 3.6 + 60)))
    plot_px = 620
    top_px = 80
    bottom_margin = xaxis_px + legend_px
    fig.update_layout(
        autosize=True,
        width=None,
        height=top_px + plot_px + bottom_margin,
        barmode='stack',
        bargap=0.35,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title=dict(
                text='Alternatives',
                font=bar_axtitle_font,
                ),
            # "Ranking" should actually read as a ranking: tallest bar first.
            categoryorder='total descending',
            tickfont=bar_tick_font,
            tickangle=-30,
            automargin=False,
            showgrid=False,
            showline=True,
            linecolor='rgba(0,0,0,0.55)',
            linewidth=1,
            ),
        yaxis=dict(
            title=dict(
                text='Scores',
                font=bar_axtitle_font,
                ),
            tickfont=bar_tick_font,
            showgrid=True,
            gridcolor='rgba(0,0,0,0.10)',
            zeroline=False,
            rangemode='tozero',
            showline=True,
            linecolor='rgba(0,0,0,0.55)',
            linewidth=1,
            ),
        legend=dict(
            orientation='h',
            font=legend_font,
            yanchor='top',
            # Paper coords: the plot area spans 0..1, so this places the top of
            # the legend exactly xaxis_px below it.
            y=-(xaxis_px / plot_px),
            xanchor='center',
            x=0.5,
            traceorder='normal',
            itemwidth=30,
            bgcolor='rgba(0,0,0,0)',
            ),
        margin=dict(l=70, r=30, t=top_px, b=bottom_margin, pad=4),
        hovermode='x unified',
        title=dict(
            text="Alternative Ranking",
            font=bar_title_font,
            x=0.5,
            xanchor='center',
            ),
        font=text_fontdict
        )
    # selector: the totals annotation is a Scatter trace and has no
    # marker.pattern, so restrict this to the bars.
    fig.update_traces(
        marker=dict(
            pattern=dict(fgcolor=hatch_color)
            ),
        selector=dict(type='bar')
        )
    return fig

## Pie Plot
def make_pie_fig(df, df_colors=None, title=None, center_text=None, is_scores=False, hatch_color='black'):
    # Get data to plot depending if we plot alternative scores or criteria weights
    if is_scores:
        alternative_df = df[df['Alternatives']==title].transpose()
        alternative_df = alternative_df.reset_index().drop(0)
        alternative_df = alternative_df.rename(columns={'index':'Criteria'})
        alternative_df.columns = ['Weight' if isinstance(col, (int, float)) else col for col in alternative_df.columns]
        data_df = alternative_df
    else:
        data_df = df
    values = data_df['Weight'].to_list()
    labels = data_df['Criteria'].to_list()
    if is_scores:
        center_text = '{:.2f}'.format(sum(values))
    else:
        center_text = 'CR={:.2f}'.format(center_text)
    # Generate Pie fig
    # With ~20 slices the outside percentage labels collide with each other.
    # Hide the ones below 3%: they are unreadable anyway and the exact figure
    # is still available on hover and in the legend.
    _total = sum(values) or 1
    _slice_labels = [f'{v / _total:.1%}' if v / _total >= 0.03 else ''
                     for v in values]
    trace = go.Pie(
            labels=labels,
            values=values,
            text=_slice_labels,
            textinfo='text',
            title=dict(
                text=center_text,
                font=dict(family='Courier New', size=15, weight='bold')
                ),
            textfont=dict(family='Courier New', size=11, weight='bold'),
            hole=0.3,
            scalegroup='one',
            )
    if isinstance(df_colors, pd.DataFrame):
        data_df = data_df.merge(df_colors[['Criteria', 'Color', 'Color Plotly', 'Hatches']], on='Criteria', how='left')        
        colors = data_df['Color Plotly'].to_list()
        # A left-merge yields NaN for any label missing from the colour table
        # (e.g. orphaned Alternative Rating entries left behind by a renamed or
        # deleted criterion). Coerce those to neutral values instead of
        # crashing with "object of type 'float' has no len()".
        hatches = ['' if not isinstance(h, str) else h
                   for h in data_df['Hatches'].to_list()]
        colors = [None if not isinstance(c, str) else c for c in colors]
        sizes = [16/len(s) if len(s) > 0 else 16 for s in hatches]
        hatches = [s[0] if len(s) > 0 else '' for s in hatches]
    fig = go.Figure(data=[trace])
    if isinstance(df_colors, pd.DataFrame):
        fig.update_traces(
            marker=dict(
                colors=colors, 
                pattern=dict(shape=hatches, fillmode='overlay', size=sizes, fgcolor=hatch_color),
                #  line=dict(color='DarkSlateGrey')
                #  line=dict(color=hacth_color, width=2)
                )
            )
    fig.update_traces(
            hovertemplate="%{label} <br>Weight: %{percent}", 
            textposition='outside',
            rotation=0           
            )
    # Same treatment as the ranking chart: the report body is capped at 210mm
    # (~780px), so a hard-coded 1000x1000 canvas overflowed the page and the
    # right-hand legend (x=1.1) fell off it entirely. Go responsive and move
    # the legend underneath.
    n_slices = len(labels)
    pie_legend_font = dict(legend_fontdict)
    pie_legend_font['size'] = 12
    pie_title_font = dict(figtitle_fontdict)
    pie_title_font['size'] = 18
    # Same row estimate as the ranking chart, so the reserved space matches the
    # number of rows the legend actually wraps into at the rendered width.
    _longest = max((len(str(l)) for l in labels), default=10)
    _per_row = max(1, int(REPORT_CHART_WIDTH / (_longest * 7.2 + 55)))
    bottom_margin = 45 + 24 * max(1, -(-n_slices // _per_row))
    fig.update_layout(
            autosize=True,
            width=None,
            height=460 + bottom_margin,
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                orientation='h',
                font=pie_legend_font,
                yanchor='top',
                y=-0.04,
                xanchor='center',
                x=0.5,
                bgcolor='rgba(0,0,0,0)'),
            margin=dict(t=55, b=bottom_margin, l=20, r=20),
            title=dict(
                text=title,
                font=pie_title_font,
                x=0.5,
                xanchor='center'),
            )
    
    return fig

def assign_colors_and_hatches(tree_dict, hatches = ['/', '\\', '|', '+', 'x', '.', '-'], alpha0=0.80, delta_alpha=0.25, min_alpha=0.3, color_scale='accent'):
#  def assign_colors_and_hatches(tree_dict, hatches = ['/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*'], alpha0=0.80, delta_alpha=0.05, min_alpha=0.3, color_scale='managua'):
    tree = CombinedTree()
    tree.from_dict(tree_dict)
    depth = tree.treelib_tree.depth()
    # Assign base colors to each main criteria
    criteria_list = [node.identifier for node in tree.treelib_tree.children(tree.root)]
    criteria_colors_list = list(COLOR_SCALES[color_scale](np.linspace(0,1,len(criteria_list))))
    df_dict = {
            'Criteria': criteria_list.copy(),
            'Color': criteria_colors_list,
            'Hatches': ['']*len(criteria_list)
            }
    for criteria, criteria_color in zip(criteria_list, criteria_colors_list):
        #  print(criteria)
        symbol_index = 0
        node_list = [node.identifier for node in tree.treelib_tree.subtree(criteria).all_nodes() if node.identifier is not criteria]
        # Assign colors based on main criteria color and adjust alpha depending on level
        for  i, node in enumerate(node_list):
            if i < len(hatches):
                node_symbol = hatches[i]
            else:
                mult = (i - len(hatches)) // len(hatches) + 2
                index = (i -  len(hatches)) % len(hatches)
                #  print('mult={}'.format(mult))
                #  print('index={}'.format(index))
                node_symbol = mult*hatches[index]
            #  print(node)
            #  print(node_symbol)
            level = tree.treelib_tree.level(node)
            #  print(level)
            node_color = criteria_color.copy()
            node_color[-1] = max(min_alpha, 1.0 - delta_alpha*(level-1))
            df_dict['Criteria'].append(node)
            df_dict['Color'].append(node_color)
            df_dict['Hatches'].append(node_symbol)
            symbol_index += 1
            #  print(df_dict)
    final_df = pd.DataFrame(df_dict)             
    final_df['Color Plotly'] = [f"rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {a})" for r, g, b, a in final_df['Color']]
    #  final_df.to_csv('criteria_colors.csv')
    return final_df

def autopct_generator(limit):
    """Remove percent on small slices."""
    def inner_autopct(pct):
        return ('%.2f%%' % pct) if pct > limit else ''
    return inner_autopct

def make_double_pie_fig_plotly(data_df, df_colors, anotate=False, pct_limit=2.0, hatch_color='black'):
    #  print(df_colors)
    # Generate Pie fig
    ncols = data_df.shape[1]
    path = ['Level{}'.format(n) for n in range(1,ncols)]

    data_df['Label'] = data_df[path].apply(lambda row: next((x for x in reversed(row) if pd.notna(x)), None), axis=1)

    fig = px.sunburst(
            data_df,
            path=path,
            values = 'Weight',
            #  color = 'Label',
            #  color_discrete_map = dict(zip(df_colors['Criteria'], df_colors['Color Plotly']))
            #  labels=data_df['Subcriteria'], 
            #  values=data_df['Weight'], 
            #  parents=data_df['Criteria'],
            #  texttemplate="%{percent:.2%}",
            #  textfont=axtitle_fontdict,
            #  hole=0.3,
            #  scalegroup='one',
            )
    #  fig = go.Figure(data=[trace])
    #  if isinstance(df_colors, pd.DataFrame):
        #  #  data_df = data_df.merge(df_colors[['Criteria', 'Color', 'Color Plotly', 'Hatches']], on='Criteria', how='left')        
        #  data_df = data_df.merge(df_colors[['Criteria', 'Color', 'Color Plotly', 'Hatches']], on='Criteria', how='left')        
        #  colors = data_df['Color Plotly'].to_list()
        #  hatches = data_df['Hatches'].to_list()
        #  data_df.to_csv('data.csv')
        #  fig.update_traces(
            #  marker=dict(
                #  colors=colors, 
                #  pattern=dict(shape=hatches, fillmode='overlay'),
                #  #  line=dict(color='DarkSlateGrey')
                #  line=dict(color=hatch_color, width=2)
                #  )
            #  )
    #  fig.update_traces(
            #  hovertemplate="%{label} <br>Weight: %{percent}", 
            #  textposition='outside',
            #  rotation=0           
            #  )
    fig.update_layout(
            width=1000,
            height=1000,
            legend=dict(
                font=legend_fontdict,
                yanchor='middle',
                y=0.5,
                xanchor='left',
                x=1.1),
            margin=dict(t=0, b=0, l=0, r=0),
            #  title=dict(
                #  text=title,
                #  font=figtitle_fontdict,                
                #  x=0.5),
            )
    
    return fig
    

def make_double_pie_fig(data_df, colors_df, anotate=False, pct_limit=2.0, hatch_color='black'):
    ncols = data_df.shape[1]
    font_size = 10
    size = 0.5
    font_size = mpl_fontdict['size']
    font_family = mpl_fontdict['family']
    font_weight= mpl_fontdict['weight']
    font_properties = font_manager.FontProperties(**mpl_fontdict)
    #  plt.rcParams["font.family"] = "DejaVu Sans Mono"
    #  plt.rcParams["font.size"] = font_size
    fig, ax = plt.subplots(figsize=(15, 15))
    fig.subplots_adjust(0.3,0,1,1)
    df_criteria = []
    wedges_list = []
    for level in range(1, ncols):
        key = 'Level{}'.format(level)
        if level < ncols - 1:
            df = data_df.groupby(key)['Weight'].sum().to_frame().reset_index()
            df = df.merge(colors_df[['Criteria', 'Hatches', 'Color', 'Color Plotly']], left_on=key, right_on='Criteria', how='left')
        else:
            df = data_df[[key, 'Weight']]
            df = df.merge(colors_df[['Criteria', 'Hatches', 'Color', 'Color Plotly']], left_on=key, right_on='Criteria', how='left')
            #  df.drop_duplicates(inplace=True)
        df['Color'] = df['Color'].fillna('white')
        df['Hatches'] = df['Hatches'].fillna('')
        df.drop('Criteria', axis=1, inplace=True)
        df_criteria.append(df)
        radius = (level + 1)*size
        pctdistance = 0.8
        #  df.to_csv('level{}.csv'.format(level))
        wedges, texts, autotexts = ax.pie(df['Weight'], radius=radius, colors=df['Color'], wedgeprops=dict(width=size, edgecolor=hatch_color), autopct=autopct_generator(pct_limit),  pctdistance=pctdistance, hatch=df['Hatches'])        
        wedges_list.append((wedges, texts, autotexts))
        # Make wedges corresponding to nan invisible
        nan_rows = df[df[key].isna()].index.tolist()
        for row in nan_rows:
            wedges[row].set_visible(False)
            autotexts[row].set_visible(False)
    for (wedges, texts, autotexts) in wedges_list:
        plt.setp(autotexts, size=font_size, weight="bold", color="black")
    # --- Custom grouped legend ---
    level_cols = [col for col in data_df.columns if col.startswith('Level')]
    legend_handles = []
    added = set()
    for _, row in data_df.iterrows():
        label_parts = []
        for i, col in enumerate(level_cols):
            value = row[col]
            if pd.notna(value):
                #  print(value)
                indent = "  " * i + ("|_ " if i > 0 else "")
                key = tuple(row[level_cols[:i+1]])
                if key not in added:
                    #  print(col)
                    #  print(value)
                    fcolor = colors_df[colors_df['Criteria']==value]['Color'].iloc[0]
                    hatch = colors_df[colors_df['Criteria']==value]['Hatches'].iloc[0]
                    ratio = "{:.2f}%".format(df_criteria[i][df_criteria[i][col]==value]['Weight'].iloc[0]*100.0)
                    #  print(ratio)
                    legend_handles.append(mpatches.Patch(
                        facecolor=fcolor,
                        label=f"{indent}{value} ({ratio})",
                        hatch= hatch,
                        edgecolor=hatch_color
                    ))
                    added.add(key)

    legend = ax.legend(
            handles=legend_handles, 
            loc='center left', 
            bbox_to_anchor=(1.5, 0.5), 
            #  bbox_to_anchor=(1+size*(ncols-1), 0.5), 
            #  fontsize=font_size, 
            title="Criteria & Subcriteria",
            handlelength=2,
            handleheight=1,
            prop=font_properties
            )   
    legend.get_title().set_fontproperties(font_properties)
    return fig


def make_double_pie_fig_old(data_df, colors_df, anotate=False, pct_limit=2.0, hatch_color='black'):
    font_size = 10
    size = 0.4
    font_size = mpl_fontdict['size']
    font_family = mpl_fontdict['family']
    font_weight= mpl_fontdict['weight']
    font_properties = font_manager.FontProperties(**mpl_fontdict)
    #  plt.rcParams["font.family"] = "DejaVu Sans Mono"
    #  plt.rcParams["font.size"] = font_size
    fig, ax = plt.subplots(figsize=(15, 15))
    fig.subplots_adjust(0.3,0,1,1)

    df_criteria =  data_df.groupby('Criteria')['Weight'].sum().to_frame().reset_index()
    df_criteria = df_criteria.merge(colors_df[['Criteria', 'Hatches', 'Color', 'Color Plotly']], on='Criteria', how='left')

    df_subcriteria = data_df.merge(colors_df, left_on='Subcriteria', right_on='Criteria', how='left')
    df_subcriteria.drop('Criteria_y', axis=1, inplace=True)
    df_subcriteria.rename(columns={'Criteria_x':'Criteria'}, inplace=True)

    inner_colors = df_criteria['Color']
    outer_colors = df_subcriteria['Color']
    subcriteria_sizes = df_subcriteria['Weight']
    hatches = df_subcriteria['Hatches']
    criteria_sizes = df_criteria['Weight']
    criteria_labels = df_criteria['Criteria']
    wedges1, texts1, autotexts1 = ax.pie(criteria_sizes, radius=1-size, colors=inner_colors, wedgeprops=dict(width=size, edgecolor=hatch_color), autopct='%1.1f%%',  pctdistance=0.75)
    
    wedges2, texts2, autotexts2 = ax.pie(subcriteria_sizes, radius=1, colors=outer_colors, wedgeprops=dict(width=size, edgecolor=hatch_color), autopct=autopct_generator(pct_limit), pctdistance=1.05, hatch=hatches)

    plt.setp(autotexts1, size=font_size, weight="bold", color="black")
    plt.setp(autotexts2, size=font_size-2, weight="bold", color="black")

    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    kw = dict(arrowprops=dict(arrowstyle="-"),
              bbox=bbox_props, zorder=0, va="center")

    if anotate:
        for p in autotexts2[3:9]:
            p.set_visible(False)
        for i, p in enumerate(wedges2[3:9]):
            ang = (p.theta2 - p.theta1)/2. + p.theta1
            y = np.sin(np.deg2rad(ang))
            x = np.cos(np.deg2rad(ang))
            horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
            connectionstyle = f"angle,angleA=0,angleB={ang}"
            kw["arrowprops"].update({"connectionstyle": connectionstyle})
            if i > 3:
                yloc = (1.1+(i-3)/10)*y
            else:
                yloc = (1.1+i/10)*y
            autotexts2[3+i]
            ax.annotate(autotexts2[3+i].get_text(), xy=(x, y), xytext=(0.6*np.sign(x), yloc),
                        fontsize=font_size-2,
                        fontweight='bold',
                        horizontalalignment=horizontalalignment, **kw)

    # --- Custom grouped legend ---
    legend_handles = []
    for _, crit_row in df_criteria.iterrows():
        # Add a "header" for each criteria
        legend_handles.append(mpatches.Patch(
            facecolor=crit_row['Color'],
            label=f"{crit_row['Criteria']} ({crit_row['Weight']:.1%})",
            edgecolor=hatch_color
        ))
        # Add subcriteria under this criteria
        sub_df = df_subcriteria[df_subcriteria['Criteria'] == crit_row['Criteria']]
        for _, row in sub_df.iterrows():
            legend_handles.append(mpatches.Patch(
                facecolor=row['Color'],
                label=f"   └ {row['Subcriteria']} ({row['Weight']:.1%})",
                hatch=row['Hatches'],
                edgecolor=hatch_color
            ))

    legend = ax.legend(
            handles=legend_handles, 
            loc='center left', 
            bbox_to_anchor=(1, 0.5), 
            #  fontsize=font_size, 
            title="Criteria & Subcriteria",
            handlelength=2,
            handleheight=1,
            prop=font_properties
            )   
    legend.get_title().set_fontproperties(font_properties)
    return fig

# SENSITIVITY TAB PLOTS
# Violin plot
def make_violin_fig(ranks_array, alternatives):
    """
    Generate violin plots from results of many Monte Carlo simulations of the AHP
    
    Parameters:
    -----------
        ranks_array: np.array
            Numpy array of shape (n_simulations, len(alternatives)) representing the ranks of the alternatives in each simulation
        alternatives: list
            List with strings of the alternative names
    """
    colors = [berlin[int(i * (len(berlin)-1) / (len(alternatives)-1))][1] for i in range(len(alternatives))]
    #  colors = []
    #  for i in range(len(alternatives)):
        #  index = int(i*(len(lapaz)-1) / (len(alternatives)-1))
        #  print(index)
        #  color = lapaz[index]
        #  print(color)
        #  colors.append(color)
    fig = go.Figure()
    for i, alt in enumerate(alternatives):
        fig.add_trace(go.Violin(
            y=ranks_array[:, i],
            name=alt,
            box_visible=True,
            meanline_visible=True,
            opacity=0.7,
            line_color=colors[i],
            #  fillcolor=colors[i],
            #  points='all',
            jitter=0.3,
            marker=dict(size=2, opacity=0.4, line=dict(width=0)),
            width=0.7
        ))
    fig.update_layout(
        showlegend=False,
        width=700,
        height=700,
        template="plotly_white",
        title=dict(
            text="Monte Carlo Ranking Distribution",
            #  tickfont=dict(size=16),
            font=figtitle_fontdict,
            #  categoryorder='array',
            #  categoryarray=alternatives
            x=0.5
        ),
        font=text_fontdict,
        xaxis=dict(
            title="Alternative",
            #  tickfont=dict(size=16),
            tickfont=axtick_fontdict,
            categoryorder='array',
            #  font=text_fontdict,
            categoryarray=alternatives
        ),
        yaxis=dict(
            title="Rank Position",
            tickfont=axtick_fontdict,
            #  tickfont=dict(size=16),
            gridcolor="lightgray",
            zeroline=True,
            #  font=text_fontdict,
            zerolinecolor="gray"
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font=legend_fontdict,
        ),
        margin=dict(l=60, r=40, t=80, b=60),
        violingap=0.2,
        violinmode='group'
    )
    fig.update_yaxes(autorange="reversed")  # Lower rank = better
    return fig

# Box plot
def make_box_fig(scores_array, alternatives):
    """
    Generate Box plots from results of many Monte Carlo simulations of the AHP
    
    Parameters:
    -----------
        scores_array: np.array
            Numpy array of shape (n_simulations, len(alternatives)) representing the scores of the alternatives in each simulation
        alternatives: list
            List with strings of the alternative names
    """
    colors = [berlin[int(i * (len(berlin)-1) / (len(alternatives)-1))][1] for i in range(len(alternatives))]
    fig = go.Figure()
    for i, alt in enumerate(alternatives):
        fig.add_trace(go.Box(
            y=scores_array[:, i],
            x=[alt]*len(scores_array[:, i]),
            name=alt,
            boxmean='sd',
            #  boxpoints='all',
            line_color=colors[i],
            #  fillcolor=colors[i],
            jitter=0.3,
            whiskerwidth=0.8,
            showwhiskers=True,
            opacity=0.7,
            marker=dict(size=2, opacity=0.4, line=dict(width=0))
        ))
    fig.update_layout(
        showlegend=False,
        width=700,
        height=700,
        template="plotly_white",
        title=dict(
            text="Monte Carlo Score Distribution",
            font=figtitle_fontdict,
            x=0.5
        ),
        font=text_fontdict,
        xaxis=dict(
            title="Alternative",
            #  tickfont=dict(size=16),
            tickfont=axtick_fontdict,
            categoryorder='array',
            #  font=text_fontdict,
            categoryarray=alternatives
        ),
        yaxis=dict(
            title="Aggregated Score",
            tickfont=axtick_fontdict,
            #  tickfont=dict(size=16),
            gridcolor="lightgray",
            zeroline=True,
            #  font=text_fontdict,
            zerolinecolor="gray"
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.1,
            xanchor="center",
            x=0.5,
            font=legend_fontdict,
        ),
        #  boxmode='group',
        margin=dict(l=60, r=40, t=80, b=60)
    )
    return fig

# Heatmap plot
def make_heatmap_fig(ranks_array, alternatives):
    """
    Generate heatmap plots from results of many Monte Carlo simulations of the AHP
    
    Parameters:
    -----------
        ranks_array: np.array
            Numpy array of shape (n_simulations, len(alternatives)) representing the ranks of the alternatives in each simulation
        alternatives: list
            List with strings of the alternative names
    """
    n_alts = len(alternatives)
    prob_matrix = np.zeros((n_alts, n_alts))
    # Calculate probability matrix 
    for i in range(n_alts):
        for j in range(n_alts):
            prob_matrix[i, j] = (ranks_array[:, i] == j + 1).mean()
    fig = go.Figure(data=px.imshow(
        prob_matrix,
        x=[f"Rank {k+1}" for k in range(n_alts)],
        y=alternatives,
        text_auto=".2f",
        aspect='auto',
        color_continuous_scale=lapaz,
        labels=dict(x="Rank Position", y="Alternative", color="Probability"),
        title="Ranking Probability Heatmap"
        #  colorscale='Viridis',
        #  zmin=0, zmax=1,
        #  colorbar=dict(title="Probability")
    ))
    fig.update_layout(
        width=700,
        height=700,
        template="plotly_white",
        title=dict(
            text="Ranking Probability Heatmap",
            x=0.5
        ),
        title_font=figtitle_fontdict,
        xaxis_title="Rank Position",
        yaxis_title="Alternative",
        font=text_fontdict,
        coloraxis_colorbar=dict(
            title="Probability",
            thickness=20,
            tickfont=axtick_fontdict
        )
    )
    fig.update_yaxes(tickangle=45)
    fig.update_traces(
            textfont_size=18,
            textfont_color="black"
            )
    return fig

# loading bar
def get_loading_bar():
    with open(imgpath + 'loader.gif', 'rb') as f:
        img=f.read()
    loading_bar = Image(value=img)
    return loading_bar

# Function to read files for Jinja filter
def read_file(filename):
    # print(filename)
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()

# Logo encoded in b64 for report generation
def get_logo():
    with open(imgpath + 'logo.png', 'rb') as img_file:
        b64logo = base64.b64encode(img_file.read()).decode()
    return b64logo

# Text label for consistency ratio
def build_label_text(consistency_ratio):
    """
    Returns an HTML string with a colour-coded CR badge.
    Green  CR < 0.05   — excellent
    Amber  CR < 0.10   — acceptable
    Red    CR >= 0.10  — inconsistent
    """
    cr = float(consistency_ratio) if consistency_ratio is not None else 0.0
    if cr < 0.05:
        color, bg, label = '#166534', '#f0fdf4', '✓ Consistent'
    elif cr < 0.10:
        color, bg, label = '#92400e', '#fffbeb', '⚠ Acceptable'
    else:
        color, bg, label = '#991b1b', '#fef2f2', '✕ Inconsistent'
    return (
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'font-family:Syne,sans-serif;font-size:13px;margin:4px 0">'
        f'<span style="font-weight:600;color:#64748b">Consistency Ratio</span>'
        f'<span style="font-family:DM Mono,monospace;font-size:14px;'
        f'font-weight:700;color:{color}">CR = {cr:.4f}</span>'
        f'<span style="background:{bg};color:{color};'
        f'border:1px solid {color}33;border-radius:20px;'
        f'padding:2px 10px;font-size:11px;font-weight:600">{label}</span>'
        f'</div>'
    )

# Creat a zip file
def create_zip(zip_name, file_list):
    with zipfile.ZipFile(zip_name, mode='w') as myzip:
        for filename in file_list:
            myzip.write(filename)

# Clean up temporary files
def clean_up():
    to_clean = []
    for file in FILES_TO_CLEAN:
        filename = os.path.join(tmp_dir, file)
        to_clean += glob.glob(filename)
    for file in to_clean:
        os.remove(file)
        
# Encode tuples in dict keys to be able to save as json
def encode_tuples(d):
    if isinstance(d, dict):
        return {str(k) if isinstance(k, tuple) else k: encode_tuples(v) for k, v in d.items()}
    return d
    
# Decode tuples in dict keys to be able to read from json
def decode_tuples(d):
    if isinstance(d, dict):
        new_dict = {}
        for k, v in d.items():
            new_key = eval(k) if k.startswith('(') and k.endswith(')') else k
            new_dict[new_key] = decode_tuples(v)
        return new_dict
    return d
    
def make_default_tree(key):
    default_tree = CombinedTree(default_goals[key])
    for criterion in default_criteria[key]:
        default_tree.create_node(criterion, parent=default_goals[key])
    for criterion, subcriteria_list in default_subcriteria[key].items():
        for subcriterion in subcriteria_list:
            default_tree.create_node(subcriterion, parent=criterion)
    return default_tree

def validate_inputs(out, tree_dict, criteria_compares_dict, alternatives_names, alternatives_compares_dict):
    """
    Validate AHP inputs. `out` can be either:
      - a widgets.Output()  (legacy — prints plain text)
      - a NotificationBar   (new — renders styled toast)
    Returns True if invalid, False if valid.
    """
    from .notificationBar import NotificationBar
    invalid = False
    msg = ''
    if tree_dict:
        pass  # future tree validation
    if criteria_compares_dict:
        pass  # future criteria validation
    if alternatives_names:
        if any(s.strip() == '' for s in alternatives_names):
            invalid = True
            msg = 'One or more alternatives are empty. Please fill in all alternative names.'
        elif len(alternatives_names) != len(set(alternatives_names)):
            invalid = True
            msg = 'One or more alternatives are repeated. Alternative names must be unique.'
    if alternatives_compares_dict:
        if "Rating Table" in alternatives_compares_dict.keys():
            for criteria in alternatives_compares_dict["Rating Scales Creation"].keys():
                for alternative in alternatives_compares_dict["Rating Table"].keys():
                    if (not alternatives_compares_dict["Rating Scales Creation"][criteria][-1]
                            and alternatives_compares_dict["Rating Table"][alternative][criteria]
                            not in alternatives_compares_dict["Rating Scales Creation"][criteria][:-1]):
                        invalid = True
                        msg = (f'Rating value for "{alternative} / {criteria}" is not defined '
                               f'in the Rating Scale. Check the Rating Tables tab.')
                        break
                if invalid:
                    break
    if invalid and msg:
        if isinstance(out, NotificationBar):
            out.error(msg)
        else:
            # Legacy Output widget fallback
            from IPython.display import clear_output
            with out:
                clear_output()
                from IPython.display import display, HTML
                display(HTML(
                    f'<div style="background:#fef2f2;border:1px solid #fca5a5;'
                    f'border-left:4px solid #dc2626;border-radius:8px;padding:10px 14px;'
                    f'font-family:Syne,sans-serif;font-size:13px;color:#991b1b">'
                    f'✕ {msg}</div>'
                ))
    elif not invalid and isinstance(out, NotificationBar):
        out.clear()
    return invalid

def add_msg_to_template(template, msg):
    with open(template, 'r') as f:
        html = f.read().format(msg=msg)
    return html

def validate_combobox(combo, value):
    if value not in combo.options:
        combo.add_class('invalid-rating')
    else:
        combo.remove_class('invalid-rating')

def inches_to_pixels(inches, dpi=100):
    return inches*dpi

def pixels_to_inches(pixels, dpi=100):
    return pixels/dpi


def extract_deepest_level_weights(df, weight_col='Weight'):
    level_cols = [col for col in df.columns if col.startswith('Level')]
    result = {}
    for _, row in df.iterrows():
        for col in reversed(level_cols):
            if pd.notnull(row[col]):
                result[row[col]] = row[weight_col]
                break
    return result

