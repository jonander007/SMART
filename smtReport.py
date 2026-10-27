#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /mnt/c/IDOM-SsmtReport.py1/REPO/IDOM-SsmtReport.py1/scripts/smtReport.py
import json
import subprocess
import os
import base64
from time import sleep
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import numpy as np
from collections import OrderedDict
from .ahp import Compare, Compose
from .questionaireAndMatrix import QuestionaireAndMatrix
from .utilities import REPORT_CHART_WIDTH, decode_tuples, make_default_tree, read_file, get_logo, make_double_pie_fig, make_pie_fig, make_bar_fig, assign_colors_and_hatches
from .constants import tmp_dir, text_fontdict, tab_titles, alternative_rating_options, accordion_titles, __VERSION__, write_html_config
from .combinedTree import CombinedTree
from plotly.offline import get_plotlyjs

# Resolution of the criteria-weights pie chart. At the previous value of 800
# the PNG alone was ~4 MB before base64 expansion; 200 is indistinguishable on
# screen and in print.
CHART_DPI = 200

__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Tuesday Nov 19, 2024 17:08:43 CET'
__LAST_MODIFIED__ = 'Thursday Nov 13, 2025 20:30:55 CET'

#    TODO: 
#           Add things to do here

# Check if graphviz is installed
graphviz_ok = False
try:
	output = subprocess.check_output(['dot', '-V'])
	graphviz_ok = True
except FileNotFoundError:
	graphviz_ok = False

# Get the logo in b64 encoding
b64logo = get_logo()

def smt_to_report(title, data, traceability_data=None):
    # Get Jinja template and variables
    if os.path.split(os.getcwd())[-1] == 'tests':
        template_folder = '../templates'
    else:
        template_folder = 'templates'
    file_loader = FileSystemLoader(template_folder)
    env = Environment(loader=file_loader)
    env.filters['read_file'] = read_file
    template = env.get_template('Report.html')

    # Recover data from the input data dictionary.
    # NOTE: .smt files written by older versions of SMART (and by the
    # questionnaire/aggregator pipeline) may lack optional keys such as
    # 'Descriptions'. Every optional key is read with .get() so that an old
    # case file never aborts report generation with a KeyError.
    # General Tab
    general = data.get(tab_titles[0], {})
    date = general.get('Date', '')
    author = general.get('Analyst', '')
    description = general.get('Description', '')
    # Alternatives Tab
    alternatives_raw = data[tab_titles[1]][tab_titles[1]]
    alternatives = alternatives_raw[:-1]
    ahptype = alternatives_raw[-1]
    # Criteria Tab
    criteria_tab = data[tab_titles[2]]
    criteria = criteria_tab[tab_titles[2]]
    treeplot, treeplot_is_png = generate_treeplot(criteria)
    criteria_descriptions = criteria_tab.get('Descriptions', {}) or {}
    # Generate colors
    colors = assign_colors_and_hatches(criteria)
    # Criteria Comparison Tab
    criteria_compare_dict, criteria_consistency_dict = generate_compares_plots(data[tab_titles[3]][tab_titles[3]], colors)
    # Alternative Rating Tab
    if ahptype == alternative_rating_options[0]: # Pairwise Comparison
        alternative_compare_dict, alternative_consistency_dict = generate_compares_plots(data[tab_titles[4]])
        rating_compare_dict, rating_consistency_dict = None, None
        rating_table = None
    elif ahptype == alternative_rating_options[1]: # Use Rating Scale
        alternative_compare_dict, alternative_consistency_dict = None, None
        rating_compare_dict, rating_consistency_dict = generate_compares_plots(data[tab_titles[4]][accordion_titles[1]])
        rating_table = generate_table(data[tab_titles[4]][accordion_titles[2]])
    else:
        # Unknown / missing AHP type: render the report without the
        # alternative-rating section rather than crashing on an unbound name.
        print(f'[SMART] smt_to_report: unknown AHP type {ahptype!r}')
        alternative_compare_dict, alternative_consistency_dict = None, None
        rating_compare_dict, rating_consistency_dict = None, None
        rating_table = None
    incomplete_nodes = []
    results_dict = generate_results(
            data[tab_titles[1]][tab_titles[1]],
            data[tab_titles[4]],
            data[tab_titles[2]][tab_titles[2]],
            data[tab_titles[3]][tab_titles[3]],
            colors,
            incomplete_out=incomplete_nodes,
            )
    # Build traceability section
    from datetime import datetime
    trace = traceability_data or {}
    trace.setdefault('report_generated', datetime.now().strftime('%Y-%m-%d %H:%M'))
    trace.setdefault('smart_version', __VERSION__)

    # Render the Jinja template
    render_context = dict(
        logo=b64logo,
        title=title,
        date=date,
        author=author,
        ahptype=ahptype,
        description=description,
        alternatives=alternatives,
        graphviz_ok=treeplot_is_png,
        treeplot=treeplot,
        criteria_descriptions=criteria_descriptions,
        criteria_compare_dict=criteria_compare_dict,
        criteria_consistency_dict=criteria_consistency_dict,
        alternative_compare_dict=alternative_compare_dict,
        alternative_consistency_dict=alternative_consistency_dict,
        rating_compare_dict=rating_compare_dict,
        rating_consistency_dict=rating_consistency_dict,
        rating_table=rating_table,
        criteria_weights=results_dict['Criteria Weights'],
        results_dict={key:value for key, value in results_dict.items() if key not in ['Criteria Weights']},
        version=__VERSION__,
        traceability=trace,
        incomplete_nodes=incomplete_nodes,
        # plotly.js is embedded ONCE here instead of once per figure: each
        # figure used to carry its own ~4.8 MB copy, which pushed the report
        # past 100 MB and raised MemoryError on large cases.
        plotlyjs=get_plotlyjs(),
        )
    filename = os.path.join(tmp_dir, 'Report.html')
    # Stream the render straight to disk. template.render() builds the whole
    # document as a single Python string and f.write() then makes a second
    # encoded copy of it; on a large case that peak was enough to raise
    # MemoryError. .stream().dump() writes it chunk by chunk instead.
    with open(filename, 'w', encoding='utf-8') as f:
        template.stream(**render_context).dump(f)
    # Safety net: never ship a report whose charts cannot render, and make the
    # chart containers break out of the A4-width column.
    _inject_report_assets(filename)


# Sentinel used to detect whether the plotly.js bundle already made it into the
# rendered report (i.e. whether templates/Report.html carries {{ plotlyjs }}).
_PLOTLYJS_SENTINEL = 'plotly.js v'

# The base template caps the report body at 210mm (~780px) for A4 printing.
# That leaves the charts squeezed into a narrow column with a lot of empty
# space either side on screen. This lets the chart containers break out of that
# column up to REPORT_CHART_WIDTH, while print keeps the original A4 width.
_FULLBLEED_SENTINEL = '/* smart-fullbleed */'
_FULLBLEED_CSS = '''<style>%s
.image-container {
    width: min(%dpx, 94vw);
    position: relative;
    left: 50%%;
    transform: translateX(-50%%);
    margin-top: 18px;
    margin-bottom: 18px;
}
@media print {
    .image-container {
        width: 100%%;
        left: 0;
        transform: none;
    }
}
</style>''' % (_FULLBLEED_SENTINEL, REPORT_CHART_WIDTH)


def _inject_report_assets(filename):
    """Guarantee the report carries the plotly.js bundle and the chart CSS.

    Figures are written with include_plotlyjs=False, so the bundle has to come
    from templates/Report.html via {{ plotlyjs }}. If that template has not
    been updated, every chart renders as an empty box and the report looks
    blank. Rather than failing silently, inject the bundle here.

    Works in a streaming fashion so memory use stays flat.
    """
    chunk_size = 1 << 20
    # 1) What is already in the file?
    markers = {_PLOTLYJS_SENTINEL: False, _FULLBLEED_SENTINEL: False}
    longest = max(len(m) for m in markers)
    tail = ''
    with open(filename, 'r', encoding='utf-8') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            window = tail + chunk
            for m in markers:
                if not markers[m] and m in window:
                    markers[m] = True
            if all(markers.values()):
                return False
            tail = chunk[-longest:]
    # 2) Something is missing: rewrite the file, injecting it after <body>.
    script = ''
    if not markers[_PLOTLYJS_SENTINEL]:
        print('[SMART] templates/Report.html has no {{ plotlyjs }} placeholder; '
              'injecting plotly.js automatically. Update the template to '
              'silence this warning.')
        script += '<script type="text/javascript">' + get_plotlyjs() + '</script>'
    if not markers[_FULLBLEED_SENTINEL]:
        script += _FULLBLEED_CSS
    tmp_path = filename + '.tmp'
    injected = False
    with open(filename, 'r', encoding='utf-8') as src, \
         open(tmp_path, 'w', encoding='utf-8') as dst:
        while True:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            if not injected:
                idx = chunk.find('<body')
                if idx != -1:
                    end = chunk.find('>', idx)
                    if end != -1:
                        dst.write(chunk[:end + 1])
                        dst.write(script)
                        dst.write(chunk[end + 1:])
                        injected = True
                        continue
            dst.write(chunk)
    if not injected:
        # No <body> tag found (unusual base template): prepend instead.
        os.replace(tmp_path, filename)
        return False
    os.replace(tmp_path, filename)
    return True


def generate_results(alternatives, alternative_rating_dict, criteria, criteria_compare_dict, colors, incomplete_out=None):
    file_dict = {}
    tree = CombinedTree()
    tree.from_dict(criteria)
    hierarchy = tree.get_hierarchy()
    alternatives_list = alternatives[:-1]
    ahptype = alternatives[-1]
    compose = Compose()
    criteria_compares = generate_compare_objects(criteria_compare_dict)
    if ahptype == alternative_rating_options[0]: # Pairwise Comparison
        alternative_compares = generate_compare_objects(alternative_rating_dict)
    else:
        alternative_compares = generate_compare_objects(alternative_rating_dict, is_rating_scale=True)
    compose.add_comparisons(
            list(criteria_compares.values()) + list(alternative_compares.values())
            )
    # Pre-flight: every node of the hierarchy needs a Compare object, otherwise
    # ahp.py fails with the opaque message "A Compare object is either
    # misconfigured or missing from the hierarchy."
    #
    # Rather than aborting, synthesise a NEUTRAL (equal-weight) Compare for
    # every missing node so that a partially filled case still produces a full
    # report. The affected nodes are collected in `incomplete_out` so the
    # report can flag them clearly as "not filled in".
    available = set(criteria_compares) | set(alternative_compares)
    required = set(hierarchy) | {c for children in hierarchy.values() for c in children}
    missing = sorted(required - available)
    synthesized = []
    for node in missing:
        children = hierarchy.get(node)
        if children and len(children) == 1:
            # A criterion with a SINGLE subcriterion never gets a Compare
            # object, because there is nothing to compare pairwise. Its child
            # necessarily carries the full weight (1.0): this is exact, not an
            # assumption, so it is synthesised silently and NOT reported as
            # incomplete data.
            criteria_compares[node] = Compare(node, {children[0]: 1.0})
            compose.add_comparisons([criteria_compares[node]])
            continue
        if children:
            # Internal criterion with no pairwise data -> children weigh equally
            items, kind = list(children), 'criteria comparison'
            neutral = Compare(node, {item: 1.0 for item in items})
            criteria_compares[node] = neutral
        else:
            # Leaf criterion with no alternative rating -> alternatives tie
            items, kind = list(alternatives_list), 'alternative rating'
            neutral = Compare(node, {item: 1.0 for item in items},
                              is_rating=(ahptype != alternative_rating_options[0]))
            alternative_compares[node] = neutral
        compose.add_comparisons([neutral])
        synthesized.append((node, kind))
        print(f'[SMART] generate_results: no {kind} data for {node!r}; '
              f'using equal weights across {len(items)} items')
    if incomplete_out is not None:
        incomplete_out.extend(synthesized)
    compose.add_hierarchy(hierarchy)
    alternatives_scores = {}
    for alternative in alternatives_list:
        alternatives_scores[alternative] = {}
        for criteria in alternative_compares.keys():
            alternatives_scores[alternative][criteria] = compose[criteria]['global_weights'][alternative]
    data = {alternative: compose[tree.root]['target_weights'][alternative] for alternative in alternatives_list}
    ranking = OrderedDict(reversed(sorted(data.items(), key=lambda x:x[1])))
    # Double pie plot with criteria/subcriteria weights
    weights_df = get_criteria_weights(criteria_compares, tree)
    fig = make_double_pie_fig(weights_df, colors)
    im_file = f'Criteria_weights.png'
    im_file = os.path.join(tmp_dir, im_file)
    # Save plot and add it to the dict
    fig.savefig(im_file, dpi=CHART_DPI, bbox_inches='tight')
    with open(im_file, 'rb') as img_file:
         b64img = base64.b64encode(img_file.read()).decode()
    file_dict['Criteria Weights'] = b64img
    # Generate the bar plot with the ranking
    alternatives_df = get_weighted_scores(alternatives_list, alternative_compares, compose)
    fig = make_bar_fig(alternatives_df, colors)
    im_file = f'Global_Ranking_Scores.html'
    im_file = os.path.join(tmp_dir, im_file)
    # Save plot and add it to the dict
    fig.write_html(im_file, full_html=False, include_plotlyjs=False,
                       default_width='100%', config=write_html_config)
    file_dict['Global Ranking'] = im_file
    # Pie plots with alternatives scores
    for alternative in ranking.keys():
        fig = make_pie_fig(alternatives_df, colors, title=alternative, is_scores=True)
        im_file = f'{alternative}_Scores.html'
        im_file = os.path.join(tmp_dir, im_file)
        # Save plot 
        fig.write_html(im_file, full_html=False, include_plotlyjs=False,
                       default_width='100%', config=write_html_config)
        file_dict[alternative] = im_file
    # Save tables
    for weights in ['global_weights', 'local_weights']:
        df = get_weighted_scores(alternatives_list, alternative_compares, compose, weights)
        df_file = '{}.html'.format(weights)
        df_file = os.path.join(tmp_dir, df_file)
        df.to_html(df_file, float_format='%.3f')
        file_dict[weights] = df_file
    return file_dict

def get_criteria_weights(criteria_compares, tree):
    #  df = pd.DataFrame([], columns=['Criteria', 'Subcriteria', 'Weight'])
    depth = tree.treelib_tree.depth()
    leafs = list(tree.treelib_tree.filter_nodes(lambda n: n.is_leaf(tree.treelib_tree.identifier)))
    #  print(depth)
    weights = {}
    # Start at level 0 (the root/goal). The root's Compare object holds the
    # global weights of the level-1 criteria; skipping it left every criterion
    # without subcriteria (a level-1 leaf) with a NaN weight, which later blew
    # up matplotlib's pie chart ("cannot convert float NaN to integer").
    for level in reversed(range(0, depth)):
        nodes = tree.get_node_names(level=level)
        for node in nodes:
            if tree.get_treelib_node(node) in leafs:
                continue
            compare = criteria_compares.get(node)
            if compare is None or not getattr(compare, 'global_weights', None):
                print(f'[SMART] get_criteria_weights: no Compare for {node!r}, skipped')
                continue
            weights = weights | compare.global_weights
    leaves = tree.treelib_tree.leaves()
    paths = []
    for leaf in leaves:
        path = tree.treelib_tree.rsearch(leaf.identifier)
        path_names = [tree.treelib_tree[node_id].tag for node_id in reversed(list(path)) if tree.treelib_tree[node_id].tag != tree.root]
        paths.append(path_names)
    df = pd.DataFrame(paths)
    df.columns = [f"Level{i+1}" for i in range(df.shape[1])]
    df['Weight'] = df.apply(lambda row: weights.get(row.dropna().iloc[-1], np.nan), axis=1)
    # Last-resort safety net: a NaN weight is not plottable. Warn and drop the
    # row instead of letting it propagate into the pie chart.
    if df['Weight'].isna().any():
        missing = df[df['Weight'].isna()].iloc[:, 0].tolist()
        print(f'[SMART] get_criteria_weights: missing weights for {missing}, dropped')
        df = df[df['Weight'].notna()].reset_index(drop=True)

    return df

def get_weighted_scores(alternatives_names, alternative_compares, compose, weights='global_weights'):
    scores = {}
    for alternative in alternatives_names:
        scores[alternative] = {}
        for criteria in alternative_compares.keys():
            scores[alternative][criteria] = compose[criteria][weights][alternative]
    final_df = pd.DataFrame(scores)
    final_df = final_df.transpose()
    final_df.reset_index(names='Alternatives', inplace=True)
    #  final_df.to_csv('final_df.csv')
    return final_df


def renormalize_rating_scales(rating_compares):
    renormalized_weights = {}
    for subcriterion in rating_compares.keys():
        max_val = max(rating_compares[subcriterion].local_weights.values())
        renormalized_weights[subcriterion] = {k:v/max_val for k,v in rating_compares[subcriterion].local_weights.items()}
    return renormalized_weights
    
def generate_compare_objects(compare_dict, precision=5, is_rating_scale=False):
    out = {}
    if is_rating_scale:
        rating_scales = compare_dict[accordion_titles[0]]
        rating_tables = compare_dict[accordion_titles[2]]
        rating_compares = generate_compare_objects(compare_dict[accordion_titles[1]])
        renormalized_weights = renormalize_rating_scales(rating_compares)
        for subcriterion, scale in rating_scales.items():
            subcriterion_data = {}
            #  print(scale)
            if scale[-1]:
                for alternative in rating_tables.keys():
                    subcriterion_data[alternative] = rating_tables[alternative][subcriterion]
            else:
                for alternative in rating_tables.keys():
                    subcriterion_data[alternative] = renormalized_weights[subcriterion][rating_tables[alternative][subcriterion]]
            out[subcriterion] = Compare(subcriterion, subcriterion_data, is_rating=True)
    else:
        for parent, questionaire in compare_dict.items():
            ahp_compare = Compare(parent, questionaire, precision=precision)
            out[parent] = ahp_compare
    return out

def generate_table(table_dict):
    df = pd.DataFrame(table_dict)
    filename = 'rating_table.html'
    filename = os.path.join(tmp_dir, filename)
    df.to_html(filename, float_format='%.3f')
    return filename

def generate_matrix(questionaires):
    criteria = sorted(set(c for pair in questionaires.keys() for c in pair))
    n = len(criteria)
     # Create an empty matrix filled with ones (diagonal is already 1)
    matrix = np.ones((n, n))
     # Map criteria names to indices
    criteria_index = {criteria[i]: i for i in range(n)}
     # Fill the upper triangle using the dictionary values
    for (crit1, crit2), value in questionaires.items():
        i, j = criteria_index[crit1], criteria_index[crit2]
        matrix[i, j] = value
        matrix[j, i] = 1 / value  # Fill the reciprocal in the lower triangle
    df = pd.DataFrame(data=matrix, index=criteria, columns=criteria)
    return df

def generate_compares_plots(compare_dict, colors=None, precision=5, is_rating=False):
    file_dict = {}
    consistency_dict = {}
    for criterion, questionaire_dict in compare_dict.items():
      # One bad/empty criterion must not take the whole report down: skip it
      # and carry on with the rest.
      try:
        if not questionaire_dict:
            print(f'[SMART] generate_compares_plots: {criterion!r} has no data, skipped')
            continue
        # Generate ahp Compare object
        ahp_compare = Compare(criterion, questionaire_dict, precision=precision)
        criteria_df = pd.DataFrame(columns=['Criteria', 'Weight'])
        for criteria, weight in ahp_compare.local_weights.items():
            criteria_df = pd.concat([pd.DataFrame([[criteria, weight]], columns=criteria_df.columns),criteria_df if not criteria_df.empty else None], ignore_index=True)
        # Generate weights plots
        fig = make_pie_fig(criteria_df, colors, title=criterion, center_text=ahp_compare.consistency_ratio)
        im_file = f'{criterion}_CR{ahp_compare.consistency_ratio}.html'
        im_file = os.path.join(tmp_dir, im_file)
        # Save plot and matrix
        fig.write_html(im_file, full_html=False, include_plotlyjs=False,
                       default_width='100%', config=write_html_config)
        df_file = f'{criterion}.html'
        df_file = os.path.join(tmp_dir, df_file)
        # Build pairwise matrix
        matrix_df = generate_matrix(questionaire_dict)
        matrix_df.to_html(df_file, float_format='%.3f')
        file_dict[criterion] = (df_file, im_file)
        consistency_dict[criterion] = ahp_compare.consistency_ratio
      except Exception as e:
        print(f'[SMART] generate_compares_plots failed for {criterion!r}: {e}')
    return file_dict, consistency_dict

def generate_treeplot(tree_dict):
    """Build the criteria tree image (or text fallback) for the report.

    A failure here must never abort the whole report: the tree plot is
    decorative, the rest of the report is not.

    Returns a (content, is_png) tuple so the caller/template knows whether to
    embed an <img> or plain text.
    """
    try:
        tree = make_default_tree('empty')
        tree.from_dict(tree_dict)
        tree_file = tree.plot()
        # Decide by extension, not by graphviz_ok: plot() falls back to text
        # if the Graphviz rendering fails for any reason.
        if str(tree_file).lower().endswith('.png'):
            with open(tree_file, 'rb') as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8'), True
        with open(tree_file, 'r', encoding='utf-8') as txt_file:
            return txt_file.read().replace("\n", "<br>").replace(" ", "&nbsp;"), False
    except Exception as e:
        print(f'[SMART] generate_treeplot failed: {e}')
        return '(criteria tree could not be rendered)', False

