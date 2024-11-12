from dash import Dash, html, dcc, callback, Output, Input, ALL, State, callback_context
from dash._utils import AttributeDict
from dash.exceptions import PreventUpdate
import json
import uuid

PROPERTY_OPTIONS = [
    {
        "label": "Electrical Conductivty",
        "value": "elec_cond_300k_low_doping"
    },
    {
        "label": "Thermal Conductivty",
        "value": "therm_cond_300k_low_doping"
    },
    {
        "label": "Bulk Modulus",
        "value": "bulk_modulus"
    },
    {
        "label": "Shear Modulus",
        "value": "shear_modulus"
    },
    {
        "label": "Universal Anisotropy",
        "value": "universal_anisotropy"
    }
]


all_prop_names = [p['value'] for p in PROPERTY_OPTIONS]
def get_prop_human_readable_name(prop_val):
    filtered = [p for p in PROPERTY_OPTIONS if p['value'] == prop_val]
    return filtered[0]['label']

PROP_SELECTOR_ID = 'property-selector'
MATERIAL_BOUNDS_CONTAINER = 'material-bounds-container'
ADD_MATERIAL_BUTTON_ID = 'add-material-button'
BOUNDS_STORE_ID = "bounds-store"
NUM_MATERIALS_VAL_ID = "number-materials"
PROPERTY_TARGET_CONTAINER_ID = "property-target-container"
GENETIC_ALGO_RESULT_ID = "genetic-algorithm-result-container"


RUN_GENETIC_ALGO_BUTTON_ID = "run-genetic-algor-button"
TOP_DESIGNS_TABLE_ID = "top-designs-table"
GENETIC_CONVERGENCE_PLOT_ID = "genetic-convergence-plot-id"
BEST_DESIGN_COMPOSITION_ID = "best-design-composition-chart"

bounds_store = dcc.Store(BOUNDS_STORE_ID, data=[])

layout = [
    html.Div([
        html.H1(children='Hashin-Shtrikman Composite Designer', className="title is-1"),
        html.Div([
            html.H3(children=["1. Please select # of materials and properties"], className="title is-4"),
            html.Div(
                [   
                    html.Strong("Properties: ", className="column one-third"),
                    html.Div(
                        [dcc.Dropdown(PROPERTY_OPTIONS, id=PROP_SELECTOR_ID, multi=True)],
                        className="column two-thirds"
                    )
                ],
                className="columns"
            ),
            html.Div(
                [
                    html.Div(
                        id=MATERIAL_BOUNDS_CONTAINER
                    ),
                    html.Button("Add Material", id=ADD_MATERIAL_BUTTON_ID, n_clicks=0, className="button")
                ],
            )],
            className="box",
        ),
        html.Div([
            html.H3(children=["2. Specify target properties"], className="title is-4"),
            html.Div(id=PROPERTY_TARGET_CONTAINER_ID)
        ], className="box"),
        html.Div([
            html.H3("3. Run Genetic Algorithm", className="title is-4"),
            html.Button("Run Genetic Algorithm", className="button", n_clicks=0, id=RUN_GENETIC_ALGO_BUTTON_ID),
            html.Div([], id=GENETIC_ALGO_RESULT_ID),
            dcc.Graph(id=TOP_DESIGNS_TABLE_ID),
            dcc.Graph(id=GENETIC_CONVERGENCE_PLOT_ID),
            dcc.Graph(id=BEST_DESIGN_COMPOSITION_ID),
        ],className="box")
        
    ], className="container"),
    bounds_store,
]

def get_bounds_selector_id(prop_name, mat_id):
    return {
        "type": "property-bounds-range-selector",
        "prop_name": prop_name,
        "mat_id": mat_id
    }

def get_bounds_form(mat_id, prop_name, low_lim, up_lim, curr_val):
    readable_prop_name = get_prop_human_readable_name(prop_name)
    return html.Div([
        html.Div([html.Strong(readable_prop_name)], className="column one-half"),
        html.Div([
            dcc.RangeSlider(low_lim, up_lim, id=get_bounds_selector_id(prop_name, mat_id), value=curr_val),
        ], className="column one-half"),
    ], className="columns")


@callback(
    Output(BOUNDS_STORE_ID, "data"),
    Input(PROP_SELECTOR_ID, "value"),
    Input({"type": "property-bounds-range-selector", "prop_name": ALL, "mat_id": ALL}, "value"),
    Input(ADD_MATERIAL_BUTTON_ID, "n_clicks"),
    Input({"type": "delete-material", "mat_id": ALL}, "n_clicks"),
    State(BOUNDS_STORE_ID, "data"),
)
def update_stored_bounds(prop_selection, all_range_selections, num_materials, deleted_clicks, stored_bounds):

    ctx = callback_context
    
    if len(ctx.inputs_list) == 0:
        return
    
    prop_selection = ctx.inputs_list[0].get('value', [])
    if stored_bounds is None:
        stored_bounds = []

    if ctx.triggered_id == ADD_MATERIAL_BUTTON_ID:
        mat_id = str(uuid.uuid4())
        new_bounds = {
            "mat_id": mat_id,
            "bounds": {}
        }
        for prop in prop_selection:
            new_bounds["bounds"][prop] = [0, 100]
        stored_bounds.append(new_bounds)
        return stored_bounds

    if isinstance(ctx.triggered_id, AttributeDict) and 'delete' in ctx.triggered_id['type']:
        # Load the dictionary ID
        print("ID: ", ctx.triggered_id)

        filtered_bds = []
        for sb in stored_bounds:
            if sb['mat_id'] != ctx.triggered_id['mat_id']:
                filtered_bds.append(sb)
        return filtered_bds

    # print(f"Context: ", ctx.inputs_list)
    if len(ctx.inputs_list) > 1 and type(ctx.inputs_list[1]) == list:
        current_range_selections = {}
        for range_input in ctx.inputs_list[1]:
            prop_name  = range_input['id']['prop_name']
            mat_id     = range_input['id']['mat_id']
            prop_range = range_input['value']
            if mat_id in current_range_selections:
                current_range_selections[mat_id][prop_name] = prop_range
            else:
                current_range_selections[mat_id] = {
                    prop_name: prop_range
                }
    else:
        current_range_selections = {}


    if prop_selection is not None:
        new_bounds = []

        for mat in stored_bounds:
            mat_id = mat['mat_id']
            bounds = mat['bounds']
            new_mat = {
                'mat_id': mat_id,
                'bounds': {}
            }
            for prop in prop_selection:
                if prop not in bounds:
                    new_mat['bounds'][prop] = [0, 100]
                elif mat_id in current_range_selections and prop in current_range_selections[mat_id]:
                    new_mat['bounds'][prop] = current_range_selections[mat_id][prop]
                else:
                    new_mat['bounds'][prop] = bounds[prop]
            
            new_bounds.append(new_mat)            
        return new_bounds

@callback(
    Output(MATERIAL_BOUNDS_CONTAINER, "children"),
    Input(BOUNDS_STORE_ID, "data"),
)
def redraw_bounds_container(stored_bounds_data):
    children = []
    if stored_bounds_data is not None:
        mat_counter = 0
        for material in stored_bounds_data:
            mat_id = material["mat_id"]
            prop_bounds = material["bounds"]
            mat_children = [
                html.Div([
                    html.Button("X", id={
                        "type": "delete-material",
                        "mat_id": mat_id
                    }, className="button"),
                    html.Strong(f"Material {mat_counter}", className="title is-5 material-label")
                ], className="mb-4")
            ]
            for prop_name, bounds_selection in prop_bounds.items():
                mat_children.append(get_bounds_form(mat_id, prop_name, 0, 100, bounds_selection))

            mat_children.append(html.Hr())
            mat_counter += 1
            children.append(
                html.Div(mat_children)
            )
    return children

@callback(
    Output(PROPERTY_TARGET_CONTAINER_ID, "children"),
    Input(PROP_SELECTOR_ID, "value"),
    State({"type": "target-prop-value", "prop_name": ALL}, "value")
)
def render_property_selection(selected_properties, prop_targets):
    children = []
    if selected_properties is None:
        selected_properties = []
    
    ctx = callback_context
    current_target_state = ctx.states_list[0]

    target_dict = {}
    for t in current_target_state:
        prop_name = t['id']['prop_name']
        prop_targ = t['value']
        target_dict[prop_name] = prop_targ
    
    for prop in selected_properties:
        existing = target_dict.get(prop, 0)
        child = html.Div([
            html.Strong(get_prop_human_readable_name(prop), className="column one-half"),
            html.Div([
                dcc.Input(
                    id={
                        "type": "target-prop-value",
                        "prop_name": prop
                    },
                    type="number",
                    className="input",
                    value=existing
                )
            ], className="column one-half")
        ], className="columns")
        children.append(child)

    return children

##########################################
# CODE TO FACTOR INTO SEPARATE MODULE    #
##########################################

from hashin_shtrikman_mp.core.user_input import MaterialProperty, Material, MixtureProperty, Mixture, UserInput
from hashin_shtrikman_mp.core.optimization import HashinShtrikman
from hashin_shtrikman_mp.core.member import Member


import plotly.express as px
import numpy as np

@callback(
    Output(TOP_DESIGNS_TABLE_ID, "figure"),
    Output(GENETIC_CONVERGENCE_PLOT_ID, "figure"),
    Output(BEST_DESIGN_COMPOSITION_ID, "figure"),
    Input(RUN_GENETIC_ALGO_BUTTON_ID, "n_clicks"),
    State(BOUNDS_STORE_ID, "data"),
    State(PROP_SELECTOR_ID, "value"),
    State({"type": "target-prop-value", "prop_name": ALL}, "value"),
)
def run_genetic_algo(n_clicks, bounds_state, selected_props, desired_props_state):
    if n_clicks == 0:
        raise PreventUpdate
    
    ctx = callback_context
    targets_state = ctx.states_list[2]
    # Assemble Mixture from MixtureProperty objects taken from input DOM elements
    mixture_props = []
    for t in targets_state:
        prop_name = t['id']['prop_name']
        prop_target = t['value']
        mixture_props.append(
            MixtureProperty(prop=prop_name, desired_prop=prop_target)
        )
    mixture = Mixture(name='mixture', properties=mixture_props)

    # Assemble Individual materials from Material Props
    materials = []
    for idx, mat in enumerate(bounds_state):
        mat_props = []
        for prop_name, bds in mat["bounds"].items():
            mat_props.append(
                MaterialProperty(
                    prop=prop_name,
                    lower_bound=bds[0],
                    upper_bound=bds[1],
                )
            )
        materials.append(
            Material(name=f'mat_{idx}', properties=mat_props)
        )

    print("Consolidated properties and mixture information")
    user_input = UserInput(materials=materials, mixtures=[mixture])
    print("Assembled user inputs")
    optimizer = HashinShtrikman(api_key="uJpFxJJGKCSp9s1shwg9HmDuNjCDfWbM", user_input=user_input)
    print("Running Genetic Algorithm...")
    optimizer.set_HS_optim_params(gen_counter=True)
    print("FInished running")
    best_designs_fig = optimizer.print_table_of_best_designs(rows=10, prec=2)
    print(f"Created best designs fig")
    convergence_plot_fig = optimizer.plot_optimization_results()
    print("Created convergence plot")
    best_design = Member(num_materials=optimizer.num_materials, 
                        num_properties=optimizer.num_properties,
                        values=optimizer.final_population.values[0], 
                        property_categories=optimizer.property_categories,
                        property_docs=optimizer.property_docs, 
                        desired_props=optimizer.desired_props, 
                        ga_params=optimizer.ga_params,
                        calc_guide=optimizer.calc_guide)
    _, contributions_chart = best_design.get_cost(plot_cost_func_contribs=True, return_plot=True)
    return best_designs_fig, convergence_plot_fig, contributions_chart

if __name__ == '__main__':
    app = Dash(__name__, assets_folder="./assets")
    app.layout = layout
    app.run(debug=True)