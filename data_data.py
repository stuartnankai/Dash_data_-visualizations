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

start = time.clock()
app = dash.Dash()
app.scripts.config.serve_locally = True
app.config.supress_callback_exceptions = True
temp_df = {}


def clean_file(df, filename):
    print("This is filename : ", filename)
    print("This is temp file name: ", temp_df.keys())
    df = df.iloc[:, :1]
    df.columns = ["tag"]
    df = df[df.tag.isin(["{", "}"]) == False]

    for index, row in df.iterrows():
        m = re.search('#(.+?) ', row['tag'])
        if m:
            row['tag'] = m.group()
    value_counts = df.tag.value_counts()

    df = value_counts.rename_axis('labels').reset_index(name='counts')
    elapsed = (time.clock() - start)
    print("Time used:", elapsed)  # It will run three times
    temp_df[filename] = df
    return df


app.layout = html.Div([
    html.H2("SIE-file analyser"),
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
    html.H5("Updated Table"),
    html.Div(dt.DataTable(rows=[{}], id='table')),
    html.Div(
        [
            dcc.Dropdown(
                id="dropdown",
                options=[{
                    'label': i,
                    # 'value': i
                } for i in list(temp_df)],
                value='filename'),
        ],
        style={'width': '25%',
               'display': 'inline-block'}),
    dcc.Graph(id='funnel-graph'),
])


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
                    barmode='stack')
        }

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
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            df = pd.read_fwf(io.StringIO(decoded.decode('iso-8859-1')), sep=" ", header=None)  # For swedish
            df = clean_file(df, filename)
    except Exception as e:
        print(e)
        return None

    return df


# callback table creation
@app.callback(Output('table', 'rows'),
              [Input('upload-data', 'contents'),
               Input('upload-data', 'filename')])
def update_output(contents, filename):
    if contents is not None:
        df = parse_contents(contents, filename)
        if df is not None:
            return df.to_dict('records')
        else:
            return [{}]
    else:
        return [{}]


@app.callback(
    Output('dropdown', 'options'),
    [Input('upload-data', 'filename')],
    [State('dropdown', 'options')])
def update_options(filename, existing_options):
    existing_options.append({'label': filename, 'value': filename})
    return existing_options


app.css.append_css({
    "external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"
})

if __name__ == '__main__':
    app.run_server(debug=True)
