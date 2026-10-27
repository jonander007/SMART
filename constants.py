from collections import OrderedDict
from cmcrameri import cm
import matplotlib as mpl

__VERSION__='v0.2.0'
__AUTHOR__ = 'Cristian Garrido Tamm'
__EMAIL__ = 'cristian.garrido@idom.com'
__CREATION_DATE__ = 'Monday Aug 05, 2024 16:21:47 CEST'
__LAST_MODIFIED__ = 'Monday Jul 28, 2025 11:36:54 CEST'

# Configuration
tmp_dir = 'tmp/'
template_dir = 'templates/'

# Sleep time
sleep_time = 1

# Default Values

default_goals = {
		'empty': 'Goal',
		'car': 'Selection of Car',
		'maritime-propulsion': 'Selection of SMR for maritime propulsion'
		}
default_criteria = {
		'empty': ['Criteria1', 'Criteria2', 'Criteria3'],
		'car': ['Cost', 'Safety', 'Style', 'Capacity'],
		'maritime-propulsion': ['Reactor Core Characteristics', 'Reactor System Characteristics', 'Fuel Cycle Characteristics', 'Decommissioning & Waste','Licensing Status', 'Political Considerations', 'Maritime Operational Challenges']
		}
default_subcriteria = {
		'empty': {
			'Criteria1': ['Subcriteria11', 'Subcriteria12'],
			'Criteria2': ['Subcriteria21', 'Subcriteria22'],
			'Criteria3': ['Subcriteria31', 'Subcriteria32'],
			},
		'car': {
			'Cost': ['Purchase Price', 'Fuel Cost', 'Maintenance Cost', 'Resale'],
			'Capacity': ['Cargo', 'Passenger']
			},
		'maritime-propulsion': {
        	'Reactor Core Characteristics': ['Fuel Safety', 'Coolant Toxicity', 'Source Term'],
        	'Reactor System Characteristics': ['Type', 'Dimensions', 'Weight', 'Power Scalability', 'Coolant Temperature', 'Component Qualification'],
        	'Fuel Cycle Characteristics': ['Refueling Time', 'Enrichment'],
        	'Decommissioning & Waste': ['Discharge Burnup', 'Waste Streams'],
        	#  'Costs': ['Investment Costs', 'Operating Costs', 'Life Cycle Costs'],
        	'Licensing Status': ['Licensing Initiated', 'Operational Experience'],
        	'Political Considerations': ['Safety Perception', 'Historical Mishappenings'],
        	'Maritime Operational Challenges': ['Limiting Operational Factors', 'Need for Specific Equipment']
			}
		}
default_alternatives = {
		'empty': ['Alternative1', 'Alternative2'],
		'car': ['Accord Sedan', 'Accord Hybrid', 'Pilot', 'CR-V', 'Element', 'Odyssey'],
		'maritime-propulsion': ['SEALER', 'MMR', 'KP-FHR']
		}

default_rating_scale_items = ['High', 'Medium', 'Low']
default_rating_scales = {
		'empty': {
			'Subcriteria11': default_rating_scale_items,
			'Subcriteria12': default_rating_scale_items,
			'Subcriteria21': default_rating_scale_items,
			'Subcriteria22': default_rating_scale_items,
			'Subcriteria31': default_rating_scale_items,
			'Subcriteria32': default_rating_scale_items,
			},
		'maritime-propulsion':{
			'Fuel Safety': default_rating_scale_items + [False],
			'Coolant Toxicity': default_rating_scale_items + [False],
			'Source Term': default_rating_scale_items+ [False],
			'Type': ['Loop with Forced Convection', 'Loop with Natural Convection', 'Integral']+ [False],
			'Dimensions': ['Small (< 100 m3)', 'Medium (100-300 m3)', 'Large (> 300 m3)']+ [False],
			'Weight': ['Very Heavy (> 1000 t)', 'Heavy (500-100 t)', 'Medium (250-500 t)', 'Light (< 250 t)']+ [False],
			'Power Scalabiltiy': ['Addition of units', 'Enrichment Increase', 'Resizing']+ [False],
			'Coolant Temperature': ['High (> 850 K)', 'Medium (700-800 K)', 'Low (<700 K)']+ [False],
			'Component Qualification': default_rating_scale_items+ [False],
			'Refueling Time': ['No Refueling', '>= 30 y', '< 30 y', 'Online Refueling']+ [False],
			'Enrichment': ['High (10-20 %)', 'Medium (5-10 %)', 'Low (0.7-5 %)', 'Natural (0.7 %)']+ [False],
			'Discharge Burnup': ['High (> 60 MWd/kg)', 'Medium (40-60 MWd/kg)', 'Low (< 40 MWd)']+ [False],
			'Waste Streams': default_rating_scale_items+ [False],
			'Licensing Initiated': ['Approved', 'Started', 'Work in Progress']+ [False],
			'Operational Experience': default_rating_scale_items+ [False],
			'Safety Perception': ['High', 'Low']+ [False],
			'Historical Mishappenings': ['Limited Past Reactor Issues', 'No Past Issues']+ [False],
			'Limiting Operational Factors': ['Few Limitations', 'Limited', 'Very Limited']+ [False],
			'Need for Specific Equipment': default_rating_scale_items+ [False]
			}
		}


# Contants
tab_titles = {
        0: 'General',
        1: 'Alternatives',
        2: 'Criteria',
        3: 'Criteria Comparison',
        4: 'Alternative Rating',
        5: 'Hierarchy',
        6: 'Results',
        7: 'Sensitivity',
        8: 'Compare Results'
        }
alternative_rating_options = [
		'Pairwise Comparison',
		'Use Rating Scale'
		]
accordion_titles = (
		'Rating Scales Creation',
		'Rating Scales Comparison',
		'Rating Table'
		)
saaty_scale = {
        '1': 'equally as important as',
        '2': 'equally to moderately more important than',
        '3': 'moderately more important than',
        '4': 'moderately to strongly more important than',
        '5': 'strongly more important than',
        '6': 'strongly to very strongly more important than',
        '7': 'very strongly more important than',
        '8': 'very strongly to extremely more important than',
        '9': 'extremely more important than' 
        }
# NOTE: the legacy `random_index` table (Saaty's classic estimates, n=1..12) has
# been removed. It was only used by helper.py::consistency_check, which was dead
# code with a latent UnboundLocalError for n>12. All consistency-ratio calculations
# now go through ahp.py::Compare, which uses the Donegan & Dodd (1991) table with
# linear interpolation for any matrix size up to 100x100.

perturbation_choices = ['matrix', 'weights']
# Fonts
font_size = 18

# Rendered width, in pixels, of the full-bleed chart containers in the report.
# Used to work out how many legend entries fit per row. Keep in sync with the
# .chart-fullbleed CSS injected by smtReport._inject_report_assets().
REPORT_CHART_WIDTH = 1150

# Width, in pixels, of the in-app Results-tab figures and their containers
# (ahpCalculator.py). All Results charts derive their size from this single
# number — change it here to resize them all.
plot_width = 1000
mpl_fontdict = dict(
		family="Courier New",
		size=font_size + 10,
		weight='bold'
		)
text_fontdict = dict(
		family="Courier New",
		size=font_size,
		weight='bold'
		)
figtitle_fontdict = dict(
		family="Courier New",
		size=font_size+10,
		weight='bold'
		)
axtitle_fontdict = dict(
		family="Courier New",
		size=font_size+8,
		weight='bold'
		)
axtick_fontdict = dict(
		family="Courier New",
		size=font_size+2,
		weight='bold'
		)
legend_fontdict = dict(
		family="Courier New",
		size=font_size+6,
		weight='bold'
		)

# Colors
colors = OrderedDict({
        '9': '#ff0000',
        '8': '#ff1a1a',
        '7': '#ff3333',
        '6': '#ff4d4d',
        '5': '#ff6666',
        '4': '#ff8080',
        '3': '#ff9999',
        '2': '#ffb3b3',
        '1':  '#808080',
        '-2':  '#b3b3ff',
        '-3':  '#9999ff',
        '-4':  '#8080ff',
        '-5':  '#6666ff',
        '-6':  '#4d4dff',
        '-7':  '#3333ff',
        '-8':  '#1a1aff',
        '-9':  '#0000ff'
        })
togglebutton_colors = list(colors.values())
red = '#ffcccc'
blue = '#ccccff'
transparent = '#ffffff'
yellow = '#ffff00'

# Borders
border = '2px solid #808080'

# Custom CSS styles
custom_css = """
<style>
    .widget-toggle-button:nth-child(1) {
        background-color: #ff0000;
        color: white;        
    }
    .widget-toggle-button:nth-child(2) {
        background-color: #ff1a1a;
        color: white;        
    }
    .widget-toggle-button:nth-child(3) {
        background-color: #ff3333;
        color: white;
    }
    .widget-toggle-button:nth-child(4) {
        background-color: #ff4d4d;
        color: white;
    }
    .widget-toggle-button:nth-child(5) {
        background-color: #ff6666;
        color: white;
    }
    .widget-toggle-button:nth-child(6) {
        background-color: #ff8080;
        color: white;
    }
    .widget-toggle-button:nth-child(7) {
        background-color: #ff9999;
        color: white;
    }
    .widget-toggle-button:nth-child(8) {
        background-color: #ffb3b3;
        color: white;
    }
    .widget-toggle-button:nth-child(9) {
        background-color: #808080;
        color: white;
    }
    .widget-toggle-button:nth-child(10) {
        background-color: #b3b3ff;
        color: white;
    }
    .widget-toggle-button:nth-child(11) {
        background-color: #9999ff;
        color: white;
    
    }
    .widget-toggle-button:nth-child(12) {
        background-color: #8080ff;
        color: white;
    
    }
    .widget-toggle-button:nth-child(13) {
        background-color: #6666ff;
        color: white;
    
    }
    .widget-toggle-button:nth-child(14) {
        background-color: #4d4dff;
        color: white;
    
    }
    .widget-toggle-button:nth-child(15) {
        background-color: #3333ff;
        color: white;
    
    }
    .widget-toggle-button:nth-child(16) {
        background-color: #1a1aff;
        color: white;
    
    }
    .widget-toggle-button:nth-child(17) {
        background-color: #0000ff;
        color: white;
    }
    .widget-toggle-button.mod-active {
        filter: brightness(0.8); /* Darken the background */
        color: black !important; /* Change text color */
        font-weight: bold !important; /* Make text bold */ 
    }
    .custom-bg {
        background-color: yellow;
        border: 2px solid red;
    }
    .invalid-rating {
        border: 2px solid red;
        background-color: yellow;
    }
    .jp-Notebook{
        background-color: url('templates/images/bg.jpg');
    }
    .widget-html {
        overflow: auto;
        max-height: 100%;
        display: flex;
        flex-direction: column-reverse;
    }
</style>
"""
section_label_style = dict(
                font_weight='bold',
                font_size='25px',
                    )
alternative_label_style = dict(
                font_weight='bold',
                font_size='20px',
                    )
write_html_config = {
        'toImageButtonOptions': {
			'autoscale': True,
            'format': 'svg', # one of png, svg, jpeg, webp
            'height': 1000,
            'width': 1000,
            'scale': 1 # Multiply title/legend/axis/canvas sizes by this factor
        }
    }

# DataFrame with IDOM ARIS data – loaded lazily so the app starts
# even without network / credentials.
list_name  = "IDOM-ARIS_v1"
site_url   = "https://idom-my.sharepoint.com/personal/cristian_garrido_idom_com/"

# Safe defaults used before (or instead of) the SharePoint load.
arisdf          = None
default_columns = []

def get_arisdf():
    """Load the ARIS SharePoint list on first call; returns (df, columns).

    Returns (None, []) gracefully if credentials are missing, the network
    is unreachable, or any other error occurs.
    """
    global arisdf, default_columns
    if arisdf is not None:
        return arisdf, default_columns
    try:
        from .splisttodf import splisttodf
        arisdf, default_columns = splisttodf(list_name, site_url)
        if default_columns is None:
            default_columns = []
    except Exception as e:
        print(f"Cannot load ARIS data: {e}")
        arisdf          = None
        default_columns = []
    return arisdf, default_columns

FILES_TO_CLEAN = ['*.png', '*.html', '*.zip', 'tree.txt', '*.csv', 'tmp*.smt', 'smart.uuid', 'smart.input']

error_template = 'templates/error.html'

COLOR_SCALES = {
		'batlow': cm.batlow,
		'glasgow': cm.glasgow,
		'lipari': cm.lipari,
		'navia': cm.navia,
		'hawaii': cm.hawaii,
		'buda': cm.buda,
		'imola': cm.imola,
		'oslo': cm.oslo,
		'grayC': cm.grayC,
		'nuuk': cm.nuuk,
		'devon': cm.devon,
		'lajolla': cm.lajolla,
		'bamako': cm.bamako,
		'davos': cm.davos,
		'bilbao': cm.bilbao,
		'lapaz': cm.lapaz,
		'acton': cm.acton,
		'turku': cm.turku,
		'tokyo': cm.tokyo,
		'managua': cm.managua,
		'roma': cm.roma,
		'berlin': cm.berlin,
		'vik': cm.vik,
		'tab10': mpl.colormaps['tab10'],
		'pastel1': mpl.colormaps['Pastel1'],
		'pastel2': mpl.colormaps['Pastel2'],
		'accent': mpl.colormaps['Accent'],
		'dark2': mpl.colormaps['Dark2'],
		'set1': mpl.colormaps['Set1'],
		'set2': mpl.colormaps['Set2'],
		'set3': mpl.colormaps['Set3'],
		}
