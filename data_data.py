import datetime
import dash
from dash.dependencies import Input, Output, State, Event
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt
import pandas as pd
import re
import time
import io
import base64
import plotly.graph_objs as go

# start = time.clock()
app = dash.Dash()
app.scripts.config.serve_locally = True
app.config.supress_callback_exceptions = True
temp_df = {}

colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}


def clean_file(df, filename):
    df = df.iloc[:, :1]
    df.columns = ["tag"]
    df = df[df.tag.isin(["{", "}"]) == False]

    for index, row in df.iterrows():
        m = re.search('#(.+?) ', row['tag'])
        if m:
            row['tag'] = m.group()
    value_counts = df.tag.value_counts()

    df = value_counts.rename_axis('labels').reset_index(name='counts')
    # elapsed = (time.clock() - start)
    temp_df[filename] = df  # save into database
    return df


# Functions
# file upload function
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
            df = clean_file(df, filename)
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
            df = clean_file(df, filename)
        else:
            df = pd.read_fwf(io.StringIO(decoded.decode('iso-8859-1')), sep=" ", header=None)  # For swedish
            df = clean_file(df, filename)
    except Exception as e:
        print(e)
        return None

    return df


app.layout = html.Div([
    html.H2("SIE-file analyser", style={
        'textAlign': 'center',
        # 'color': colors['text']
    }),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False),
    html.Div(id='duplicate'),
    html.H5("Recently Upload Data"),
    html.Div(dt.DataTable(rows=[{}], id='table', filterable=True, sortable=True)),
    html.Div(id='show-table'),
    html.H5("Show Statistics Chart "),
    html.Div(
        [
            dcc.Dropdown(
                id="dropdown",
                options=[{
                    'label': i,
                    # 'value': i
                } for i in list(temp_df)],
                # value='filename'
            ),
        ],
        style={'width': '25%',
               'display': 'inline-block'}),
    html.H5("Delete database"),
    html.Div(id='target'),
    dcc.Input(id='input', type='text', value='', placeholder='Type the database name'),
    html.Button(id='submit', type='submit', children='Delete', style={
        'width': '15%',
    }),
    dcc.Graph(id='funnel-graph'),
])


# Check duplicated
@app.callback(Output('duplicate', 'children'),
              [Input('upload-data', 'filename')],
              [State('dropdown', 'options')])
def callback(filename, existing_options):
    fileList = [i['label'] for i in existing_options]
    if filename in fileList:
        return "This database has been uploaded already: {}".format(filename)


# Update graph based on the database
@app.callback(
    Output('funnel-graph', 'figure'),
    [Input('dropdown', 'value')])
def update_graph(filename):
    if filename is None:
        return {
            'data': [],
            'layout':
                go.Layout(
                    title="Please select a database",
                )
        }
    else:
        df_plot = temp_df[filename]
        return {
            'data': [{'x': df_plot['labels'], 'y': df_plot['counts'], 'type': 'bar', 'name': 'data'},
                     ],
            'layout':
                go.Layout(
                    title=filename,
                    barmode='stack'
                )
        }


# callback table creation
@app.callback(Output('table', 'rows'),
              [Input('upload-data', 'contents'),
               Input('upload-data', 'filename')])
def update_output(contents, filename):
    if contents is not None:
        df = parse_contents(contents, filename)
        if df is not None:
            print("This is records: ", df.to_dict('records'))
            return df.to_dict('records')
        else:
            return [{}]
    else:
        return [{}]


# update the data list
@app.callback(
    Output('dropdown', 'options'),
    [Input('upload-data', 'filename')],
    [State('dropdown', 'options'),
     State('input', 'value')],
    [Event('submit', 'click')])
def update_options(filename, existing_options, state):
    fileList = [i['label'] for i in existing_options]
    if state in fileList:
        del temp_df[state]
        index_file = fileList.index(state)
        del existing_options[index_file]

    if filename not in fileList and filename is not None:
        existing_options.append({'label': filename, 'value': filename})
    return existing_options


# Check delete button
@app.callback(Output('target', 'children'), [], [State('dropdown', 'options'), State('input', 'value')],
              events=[Event('submit', 'click')])
def callback(existing_options, state):
    fileList = [i['label'] for i in existing_options]
    if len(state) == 0:
        if len(fileList) == 0:
            return "There is no saved database, please upload one"
        else:
            return "Please type the name of database."
    elif state in fileList:
        return "Database has been deleted: {}".format(state)
    else:
        return "Can not find this database: {}".format(state)


# Reset the input field
@app.callback(Output('input', 'value'), [], [State('dropdown', 'options'), State('input', 'value')],
              events=[Event('submit', 'click')])
def callback(existing_options, state):
    fileList = [i['label'] for i in existing_options]
    if state in fileList:
        return ""
    else:
        return state


# Clean the uploaded file name
@app.callback(Output('upload-data', 'filename'), [], [State('dropdown', 'options'), State('input', 'value')],
              events=[Event('submit', 'click')])
def callback(existing_options, state):
    fileList = [i['label'] for i in existing_options]
    if state in fileList:
        return ""


app.css.append_css({
    "external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"
})

if __name__ == '__main__':
    app.run_server(debug=True)
