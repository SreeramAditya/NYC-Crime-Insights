from flask import Flask, render_template, request, jsonify
import cx_Oracle
import pandas as pd
import plotly.graph_objs as go
import json
import plotly
from flask import Flask, render_template, request,make_response,jsonify
import cx_Oracle
import pandas as pd
import plotly.express as px
import plotly
import plotly.offline as pyo
import plotly.graph_objs as go
import json
import plotly.io as pio
app = Flask(__name__)

# Oracle database connection


@app.route('/')
def home():
    return render_template('home.html')
@app.route('/tuples')
def tuples():
    tuples=f''' SELECT SUM(row_count) AS total_row_count FROM (
    SELECT COUNT(*) AS row_count FROM spotukuchi.allegations_against_police_officers
    UNION ALL
    SELECT COUNT(*) AS row_count FROM spotukuchi.arrestee_details
    UNION ALL
    SELECT COUNT(*) AS row_count FROM spotukuchi.complaints_against_police_officers
    UNION ALL
    SELECT COUNT(*) AS row_count FROM spotukuchi.county
    UNION ALL
    SELECT COUNT(*) AS row_count FROM spotukuchi.literacy
    UNION ALL
    SELECT COUNT(*) AS row_count FROM spotukuchi.offense_details
    UNION ALL
    SELECT COUNT(*) AS row_count FROM spotukuchi.penality
    UNION ALL
    SELECT COUNT(*) AS row_count FROM spotukuchi.police_officers
    UNION ALL

    SELECT COUNT(*) AS row_count FROM sgutha.park_crimes
    UNION ALL
    SELECT COUNT(*) AS row_count FROM sgutha.park_info
    UNION ALL
    SELECT COUNT(*) AS row_count FROM "UT.SHARMA".crime
    UNION ALL
    SELECT COUNT(*) AS row_count FROM "UT.SHARMA".poverty

) subquery_alias
'''
    tuples_result = pd.read_sql(tuples, connection)
    total_row_count = tuples_result['TOTAL_ROW_COUNT'].values[0] if not tuples_result.empty else 0
    return render_template('tuples.html', total_row_count=total_row_count)



@app.route('/query3')
def query3():
    # Fetch unique values for years, crime types, and counties for the dropdowns
    years_query = "SELECT DISTINCT year FROM spotukuchi.arrestee_details ORDER BY year"
    counties_query = "SELECT DISTINCT COUNTY FROM spotukuchi.county ORDER BY COUNTY"
    bias_query="SELECT DISTINCT BIASMOTIVEDESCRIPTION FROM spotukuchi.offense_details"
    df_years = pd.read_sql(years_query, connection)
    df_counties = pd.read_sql(counties_query, connection)
    df_bias= pd.read_sql(bias_query, connection)
    #print(df_bias)
    years = df_years['YEAR'].tolist() if 'YEAR' in df_years.columns else []
    counties = df_counties['COUNTY'].tolist() if 'COUNTY' in df_counties.columns else []
    bias_type = df_bias['BIASMOTIVEDESCRIPTION'].tolist() if 'BIASMOTIVEDESCRIPTION' in df_bias.columns else []
    return render_template('query3.html', years=years, counties=counties, bias_type=bias_type)

@app.route('/update_graph_3', methods=['POST'])
def update_graph_3():
    filter_params = request.json
    #county,year,biasmotive
    selected_years = filter_params['years']
    selected_counties = filter_params['counties']
    selected_bias=filter_params['bias_type']
    # print(selected_counties)
    # print(selected_years)
    # print(selected_bias)
    start_year = min(selected_years)
    end_year = max(selected_years)
    combined_county=", ".join([f"'{element}'" for element in selected_counties])
    combined_bias=", ".join([f"'{element}'" for element in selected_bias])
    print(combined_county)
    print(combined_bias)
    query3 = f'''
        WITH AgeCategories AS (
        SELECT
        ad.Arrest_Id,
        CASE
            WHEN ad.Age < 18 THEN '<18'
            WHEN ad.Age BETWEEN 18 AND 34 THEN '18-34'
            WHEN ad.Age BETWEEN 35 AND 49 THEN '35-49'
            WHEN ad.Age BETWEEN 50 AND 64 THEN '50-64'
            ELSE '65+'
        END AS AgeCategory
    FROM
        spotukuchi.arrestee_details ad
),
RankedData AS (
    SELECT
        ad.Arrest_Id,
        ad.Year,
        ad.Quarter,
        ad.year_quarter_combined,
        ad.Race,
        ac.AgeCategory,
        od.OffenseDescription,
        od.BiasMotiveDescription,
        co.county,
        ad.Gender,
        CASE WHEN ROW_NUMBER() OVER (PARTITION BY ad.Year,ad.quarter, od.BiasMotiveDescription ORDER BY ad.Year)= 1 THEN COUNT(*) OVER (PARTITION BY ad.Year,ad.quarter, od.BiasMotiveDescription) END as TotalBias ,
        CASE WHEN ROW_NUMBER() OVER (PARTITION BY ad.Year,ad.quarter,od.BiasMotiveDescription, od.OffenseDescription ORDER BY ad.Year)=1 THEN COUNT(*) OVER (PARTITION BY ad.Year,ad.quarter,od.BiasMotiveDescription, od.OffenseDescription) END as TotalOfensecount,
        CASE WHEN ROW_NUMBER() OVER (PARTITION BY ad.Year,ad.quarter,od.BiasMotiveDescription,ad.Race,ac.AgeCategory,ad.Gender  ORDER BY ad.Year)=1 THEN COUNT(*) OVER (PARTITION BY ad.Year,ad.quarter,od.BiasMotiveDescription,ad.Race,ac.AgeCategory,ad.Gender) END as Totaldemocount
    FROM
        spotukuchi.county co
    INNER JOIN
        spotukuchi.arrestee_details ad ON co.precinct_id = ad.Precinct
    INNER JOIN
        AgeCategories ac ON ad.Arrest_Id = ac.Arrest_Id
    INNER JOIN
        spotukuchi.offense_details od ON ad.Arrest_Id = od.ArrestId
    WHERE
        ad.Year BETWEEN {start_year} AND {end_year}
        AND od.BiasMotiveDescription in ({combined_bias})

        AND co.county in ({combined_county})
        AND quarter in (1,2,3,4)
)
SELECT
    Arrest_Id,
    Year,
    Quarter,
    year_quarter_combined,
    OffenseDescription,
    BiasMotiveDescription,
    Race,
    AgeCategory,
    Gender,
    Totaldemocount, 
    
    county,
    TotalBias,
    TotalOfensecount
    FROM
    RankedData
    ORDER BY year_quarter_combined
        '''
    query_result = pd.read_sql(query3, connection)
    query_result = query_result.sort_values(by='YEAR_QUARTER_COMBINED')
    sorted_categories = sorted(query_result['YEAR_QUARTER_COMBINED'].unique())
    query_result = query_result[query_result['TOTALBIAS'].notnull()]

    query_result = query_result.sort_values(by='YEAR_QUARTER_COMBINED')
    sorted_categories = sorted(query_result['YEAR_QUARTER_COMBINED'].unique())

# Create the bar chart
    fig = px.bar(
    query_result, 
    x='YEAR_QUARTER_COMBINED', 
    y='TOTALBIAS',
    color='BIASMOTIVEDESCRIPTION',
    facet_col='COUNTY',
    barmode='group',
    category_orders={'YEAR_QUARTER_COMBINED': sorted_categories},
    labels={'TOTALBIAS': 'Total Cases'},
    title='Total Bias Trend'
    )

    counties = query_result['COUNTY'].unique()
    biases = query_result['BIASMOTIVEDESCRIPTION'].unique()

# Add scatter plot (line) traces for each county and bias motive
    for i, county in enumerate(counties, start=1):
        for bias in biases:
        # Filter data for each county and bias motive
            line_data = query_result[(query_result['COUNTY'] == county) & (query_result['BIASMOTIVEDESCRIPTION'] == bias)]
            if not line_data.empty:
                fig.add_trace(go.Scatter(
                x=line_data['YEAR_QUARTER_COMBINED'],
                y=line_data['TOTALBIAS'],
                mode='lines+markers',
                name=f'Line - {bias} in {county}',
                legendgroup=f'{county}-{bias}',
                showlegend=True
                ), row=1, col=i) 

    

    query_result = query_result.sort_values(by='YEAR_QUARTER_COMBINED')
    sorted_categories = sorted(query_result['YEAR_QUARTER_COMBINED'].unique())

    figu_bias= px.bar(query_result, x='YEAR_QUARTER_COMBINED', y='TOTALBIAS',
            color='BIASMOTIVEDESCRIPTION',
              facet_col='COUNTY',  # Use facet_col to create subplots for each county
              barmode='group',    # Display bars side by side
              category_orders={'YEAR_QUARTER_COMBINED': sorted_categories},
              labels={'TOTALBIAS': 'Total Cases'},
              title='Total Bias Trend')
    figu_offense = px.bar(query_result, x='YEAR_QUARTER_COMBINED', y='TOTALOFENSECOUNT',
              color='OFFENSEDESCRIPTION',  # Remove the extra space
              facet_col='COUNTY',
              title='Total Offense Count Over Time',
              barmode='group',    # Display bars side by side
              category_orders={'YEAR_QUARTER_COMBINED': sorted_categories},
              labels={'TOTALOFENSECOUNT': 'Total Offense Count'})
    query_result['DemographicGroup'] = query_result['RACE'] + '-' + query_result['AGECATEGORY'] + '-' + query_result['GENDER']
    figu_demo = px.pie(
    query_result,
    names='DemographicGroup',
    values='TOTALDEMOCOUNT',
    color='DemographicGroup',
    facet_col='COUNTY',
    category_orders={'YEAR_QUARTER_COMBINED': sorted_categories},
    labels={'TOTALDEMOCOUNT': 'Total Cases'},
    title='Total Offense Trend by Demographics'
    
)

    graphsJSON = {
        'graph_trend': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
        'graph_bias': json.dumps(figu_bias, cls=plotly.utils.PlotlyJSONEncoder),
        'graph_offense': json.dumps(figu_offense, cls=plotly.utils.PlotlyJSONEncoder),
        'graph_demo': json.dumps(figu_demo, cls=plotly.utils.PlotlyJSONEncoder)
        

    }
    return graphsJSON


@app.route('/query4')
def query4():
    # Fetch unique values for years, crime types, and counties for the dropdowns
    years_query = "SELECT DISTINCT YEAR FROM sgutha.park_crimes ORDER BY YEAR"
    counties_query = "SELECT DISTINCT COUNTY FROM sgutha.park_info ORDER BY COUNTY"
    crime_types = ['MURDER', 'RAPE', 'ROBBERY', 'FELONY_ASSAULT', 'GRAND_LARCENY','GRAND_LARCENY_OF_MOTOR_VEHICLE']

    df_years = pd.read_sql(years_query, connection)
    df_counties = pd.read_sql(counties_query, connection)
    years = df_years['YEAR'].tolist() if 'YEAR' in df_years.columns else []
    counties = df_counties['COUNTY'].tolist() if 'COUNTY' in df_counties.columns else []

    return render_template('query4.html', years=years, counties=counties, crime_types=crime_types)

@app.route('/update_graph', methods=['POST'])
def update_graph():
    filter_params = request.json
    selected_years = filter_params['years']
    selected_counties = filter_params['counties']
    selected_crimes = filter_params['crime_types']

    start_year = min(selected_years)
    end_year = max(selected_years)
    crime_sum_clauses = ', '.join([f"SUM(fc.{crime}) AS total_{crime}" for crime in selected_crimes])
    
    # Adjust the query to filter by selected counties
    sql_query = f'''
    WITH FilteredCrime AS (
        SELECT 
            park_id, 
            year, 
            quarter, 
            {', '.join(selected_crimes)}
        FROM 
            sgutha.park_crimes
        WHERE 
            year >= {start_year} AND year <= {end_year}
    ),
    FilteredPark AS (
        SELECT 
            park_id, 
            county
        FROM 
            sgutha.park_info
        WHERE 
            county IN ({', '.join(["'" + county + "'" for county in selected_counties])})
    )
    SELECT 
        fp.county,
        fc.year,
        fc.quarter,
        {crime_sum_clauses}
    FROM 
        FilteredCrime fc
    JOIN 
        FilteredPark fp ON fc.park_id = fp.park_id
    GROUP BY 
        fp.county, fc.year, fc.quarter
    ORDER BY 
        fp.county, fc.year, fc.quarter
    '''

    df = pd.read_sql(sql_query, connection)
    df['Year_Quarter'] = df['YEAR'].astype(str) + ' Q' + df['QUARTER'].astype(str)
    df['YearNum'] = df['YEAR'] + df['QUARTER'] / 10
    df = df.sort_values(by='YearNum')

    fig = go.Figure()
    for crime in selected_crimes:
        crime_label = crime.replace('_', ' ').title()
        print(crime_label,crime)
        for county in df['COUNTY'].unique():
            county_data = df[df['COUNTY'] == county]
            fig.add_trace(go.Scatter(
                x=county_data['Year_Quarter'],
                y=county_data[f'TOTAL_{crime}'],
                mode='lines+markers+text',
                name=f'{crime_label} in {county}'
            ))
    
    fig.update_layout(title=f'Crime Trend in Newyork City Parks by county from {start_year} to {end_year}')
    
    df_total = df.groupby(['Year_Quarter']).sum().reset_index()
    fig_total = go.Figure()
    for crime in selected_crimes:
        fig_total.add_trace(go.Bar(
            x=df_total['Year_Quarter'],
            y=df_total[f'TOTAL_{crime}'],
            name=f'Total {crime.replace("_", " ").title()}'
        ))
    fig_total.update_layout(title=f'Total crimes over selected counties from {start_year} to {end_year}')


    total_crimes = df[[f'TOTAL_{crime}' for crime in selected_crimes]].sum()
    fig_pie = go.Figure(data=[go.Pie(
        labels=[crime.replace('_', ' ').title() for crime in selected_crimes],
        values=total_crimes,
        hole=.3  # For a donut-like pie chart
    )])
    fig_pie.update_layout(title=f'Proportion of Crime Types from {start_year} to {end_year}')


    
    df.drop(columns=['YearNum'], inplace=True)
   
    #graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    graphsJSON = {
        'graph_line': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
        'graph_total': json.dumps(fig_total, cls=plotly.utils.PlotlyJSONEncoder),
        'graph_pie': json.dumps(fig_pie, cls=plotly.utils.PlotlyJSONEncoder)
    }

    return jsonify(graphsJSON)


@app.route('/query5')
def query5():
    # Fetch unique values for years, crime types, and counties for the dropdowns
    years_query = "SELECT DISTINCT INCIDENTYEAR as YEAR FROM spotukuchi.complaints_against_police_officers ORDER BY YEAR"
    counties_query = "SELECT DISTINCT COUNTY FROM spotukuchi.county ORDER BY COUNTY"
    fado_query="SELECT DISTINCT FADOTYPE from spotukuchi.allegations_against_police_officers"
    race_query="select distinct victimallegedrace as race from spotukuchi.allegations_against_police_officers where victimallegedrace not in ('Unknown','Refused','nan') order by race"
    age_query="select distinct victimagecategory as age from spotukuchi.allegations_against_police_officers where victimagecategory!='Unknown'"

    df_years = pd.read_sql(years_query, connection)
    df_counties = pd.read_sql(counties_query, connection)
    df_fados=pd.read_sql(fado_query,connection)
    df_race=pd.read_sql(race_query,connection)
    df_age=pd.read_sql(age_query,connection)
    years = df_years['YEAR'].tolist() if 'YEAR' in df_years.columns else []

    counties = df_counties['COUNTY'].tolist() if 'COUNTY' in df_counties.columns else []

    fado_types=df_fados['FADOTYPE'].tolist() if 'FADOTYPE' in df_fados.columns else []

    race_types=df_race['RACE'].tolist() if 'RACE' in df_race.columns else []

    age_types=df_age['AGE'].tolist() if 'AGE' in df_age.columns else []


    return render_template('query5.html', years=years, counties=counties, fado_types=fado_types, race_types=race_types,age_types=age_types)

@app.route('/update_graph_5', methods=['POST'])
def update_graph_5():
    filter_params = request.json
    selected_years = filter_params['years']
    selected_counties = filter_params['counties']
    selected_fados=filter_params['fado_types']
    selected_races=filter_params['race_types']
    selected_age=filter_params['age_types']
    start_year = min(selected_years)
    end_year = max(selected_years)
    # print(selected_counties)
    # print(selected_years)
    # print(selected_fados)
    # print(selected_races)
    # print(selected_age)
    combined_race = ", ".join([f"'{element}'" for element in selected_races])
    combined_race_query=f"a.VICTIMALLEGEDRACE in ({combined_race})"

    combined_fado=", ".join([f"'{element}'" for element in selected_fados])
    combined_age=", ".join([f"'{element}'" for element in selected_age])


    combined_county=", ".join([f"'{element}'" for element in selected_counties])
    
    print(combined_county)


    query5=f"""
WITH AllegationDetails AS (
    SELECT 
        a.COMPLAINTID,
        a.VICTIMALLEGEDRACE,
        a.VICTIMAGECATEGORY,
        a.FADOTYPE,
        a.OFFICEREXPERIENCECATEGORY,
        a.ALLEGATION
    FROM 
        spotukuchi.allegations_against_police_officers a
    WHERE 
        a.VICTIMALLEGEDRACE IS NOT NULL AND
        a.VICTIMALLEGEDRACE != 'nan' AND
        a.VICTIMALLEGEDRACE != 'Unknown' AND
        a.VICTIMALLEGEDRACE != 'Refused' AND
        a.VICTIMAGECATEGORY != 'Unknown' AND
        {combined_race_query} AND
        a.FADOTYPE in ({combined_fado}) AND
        a.VICTIMAGECATEGORY in ({combined_age})
), ComplaintDetails AS (
    SELECT 
        c.COMPLAINTID,
        c.INCIDENTYEAR,
        co.COUNTY,
        c.PRECINCTOFINCIDENT
    FROM 
        spotukuchi.complaints_against_police_officers c
    INNER JOIN 
        spotukuchi.county co ON c.PRECINCTOFINCIDENT = co.precinct_id
    WHERE 
        c.INCIDENTYEAR BETWEEN {start_year} AND {end_year}
), PenaltyDetails AS (
    SELECT 
        p.COMPLAINTID,
        p.NYPDOFFICERPENALTY
    FROM 
        spotukuchi.penality p
)
SELECT 
    cd.INCIDENTYEAR,
    cd.COUNTY,
    ad.VICTIMALLEGEDRACE,
    ad.VICTIMAGECATEGORY,
    ad.FADOTYPE,
    ad.OFFICEREXPERIENCECATEGORY,
    ad.ALLEGATION,
    COUNT(*) AS NumberOfAllegations,
    pd.NYPDOFFICERPENALTY
FROM 
    AllegationDetails ad
INNER JOIN 
    ComplaintDetails cd ON ad.COMPLAINTID = cd.COMPLAINTID
LEFT JOIN 
    PenaltyDetails pd ON ad.COMPLAINTID = pd.COMPLAINTID
GROUP BY 
    cd.INCIDENTYEAR, cd.COUNTY, ad.VICTIMALLEGEDRACE, ad.VICTIMAGECATEGORY, ad.FADOTYPE, ad.OFFICEREXPERIENCECATEGORY, pd.NYPDOFFICERPENALTY,ad.ALLEGATION
ORDER BY 
    cd.INCIDENTYEAR, NumberOfAllegations
"""
    df = pd.read_sql(query5, connection)

    filtered_df = df[df['FADOTYPE'].isin(selected_fados)]
    fig = go.Figure()

  

    for county in filtered_df['COUNTY'].unique():
        county_filtered_df = filtered_df[filtered_df['COUNTY'] == county]
        for race in county_filtered_df['VICTIMALLEGEDRACE'].unique():
            race_filtered_df = county_filtered_df[county_filtered_df['VICTIMALLEGEDRACE'] == race]
            for fado_type in race_filtered_df['FADOTYPE'].unique():
                fado_filtered_df = race_filtered_df[race_filtered_df['FADOTYPE'] == fado_type]
                grouped_df = fado_filtered_df.groupby(['INCIDENTYEAR', 'VICTIMAGECATEGORY']).agg({'NUMBEROFALLEGATIONS': 'sum'}).reset_index()

            # Iterate over each age category for the specific race, FADO type, and county
                for age_category in grouped_df['VICTIMAGECATEGORY'].unique():
                    category_data = grouped_df[grouped_df['VICTIMAGECATEGORY'] == age_category]
        
                # Add a trace for this county, race, age category, and FADO type
                    fig.add_trace(go.Scatter(
                    x=category_data['INCIDENTYEAR'],
                    y=category_data['NUMBEROFALLEGATIONS'],
                    mode='lines+markers',
                    name=f'{county} - {race} Age: {age_category} FADO: {fado_type}',
                    hovertemplate=(
                        'Year: %{x}<br>'
                        'Allegations: %{y}<br>'
                        'County: ' + county + '<br>'
                        'Race: ' + race + '<br>'
                        'Age Category: ' + age_category + '<br>'
                        'FADO Type: ' + fado_type +
                        '<extra></extra>'  # Hides the trace name from the hover text
                    )
                    ))

    fig.update_layout(
    title=f'Total Number of Allegations by Year, Race, and County',
    xaxis_title='Year',
    yaxis_title='Total Number of Allegations',
    xaxis=dict(type='category', categoryorder='category ascending')
    )

    penalty_trend_df = df.groupby(['INCIDENTYEAR', 'NYPDOFFICERPENALTY']).size().reset_index(name='NumberofPenalties')
    graph_fig = go.Figure()
    for penalty_type in penalty_trend_df['NYPDOFFICERPENALTY'].unique():
        penalty_df = penalty_trend_df[penalty_trend_df['NYPDOFFICERPENALTY'] == penalty_type]
        graph_fig.add_trace(go.Scatter(
            x=penalty_df['INCIDENTYEAR'],
            y=penalty_df['NumberofPenalties'],
            mode='lines+markers',
            name=penalty_type,
            hovertemplate=(
                    'Year: %{x}<br>'
                    'Penality: ' + penalty_type + '<br>'
                    'Total Penality: %{y}<br>'
                    '<extra></extra>'  # Hides the trace name from the hover text
                )
        ))
    
    graph_fig.update_layout(
        title='Trend of Police Penalties Over Years',
        xaxis_title='Year',
        yaxis_title='Number of Penalties',
        xaxis=dict(type='category', categoryorder='category ascending')
    )

    # Aggregate data for allegations
    allegation_counts = df['ALLEGATION'].value_counts().reset_index()
    allegation_counts.columns = ['ALLEGATION', 'Count']
    top_ten_allegations = allegation_counts.head(20)

# Create the donut-like pie chart for the top ten allegations
    pie_fig = go.Figure(data=[go.Pie(
    labels=top_ten_allegations['ALLEGATION'], 
    values=top_ten_allegations['Count'],
    hole=0.4  # Adjust this value for the size of the hole
    )])

# Update the layout for the pie chart
    pie_fig.update_layout(
    title='Total Count of Top 20 Types of Allegation',
    annotations=[dict(text='', x=0.5, y=0.5, font_size=20, showarrow=False)]
    )


    officer_experience_counts = df['OFFICEREXPERIENCECATEGORY'].value_counts().reset_index()
    officer_experience_counts.columns = ['ExperienceCategory', 'Count']
    print(officer_experience_counts)

# Create the pie chart for officer experience category
    officer_experience_pie = go.Figure(data=[go.Pie(
    labels=officer_experience_counts['ExperienceCategory'], 
    values=officer_experience_counts['Count'],
    hole=0.4  # Adjust this value for the size of the hole
    )])

# Update the layout for the officer experience pie chart
    officer_experience_pie.update_layout(
    title='Distribution of Officer Experience Categories Involved in Allegations',
    annotations=[dict(text='', x=0.5, y=0.5, font_size=20, showarrow=False)]
    )


    
    graphsJSON = {
        'graph_line': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
        'graph_penalty_trend': json.dumps(graph_fig, cls=plotly.utils.PlotlyJSONEncoder),
        'allegation_chart': json.dumps(pie_fig, cls=plotly.utils.PlotlyJSONEncoder),
        'officer_experience_chart': json.dumps(officer_experience_pie, cls=plotly.utils.PlotlyJSONEncoder)
    }

    return jsonify(graphsJSON)

#ssdff

@app.route('/query1')
def query1():
    # Fetch unique values for years, crime types, and counties for the dropdowns
    years_query = "SELECT DISTINCT year FROM spotukuchi.literacy ORDER BY year"
    counties_query = "SELECT DISTINCT COUNTY FROM spotukuchi.county ORDER BY COUNTY"
    fado_query='SELECT DISTINCT crime_desc from \"UT.SHARMA\".crime'


    df_years = pd.read_sql(years_query, connection)
    df_counties = pd.read_sql(counties_query, connection)
    df_crime=pd.read_sql(fado_query,connection)
    years = df_years['YEAR'].tolist() if 'YEAR' in df_years.columns else []

    counties = df_counties['COUNTY'].tolist() if 'COUNTY' in df_counties.columns else []

    crime_types=df_crime['CRIME_DESC'].tolist() if 'CRIME_DESC' in df_crime.columns else []
    print(crime_types)
    return render_template('query1.html', years=years, counties=counties, crime_types=crime_types)

@app.route('/update_graph_1', methods=['POST'])
def update_graph_1():
    filter_params = request.json
    selected_years = filter_params['years']
    selected_counties = filter_params['counties']
    selected_crimes=filter_params['crime_types']
    # print(selected_crimes)
    # print(selected_counties)

#     selected_races=filter_params['race_types']
#     selected_age=filter_params['age_types']
    start_year = min(selected_years)
    end_year = max(selected_years)
#     # print(selected_counties)
#     # print(selected_years)
#     # print(selected_fados)
#     # print(selected_races)
#     # print(selected_age)
#     combined_race = ", ".join([f"'{element}'" for element in selected_races])
#     combined_race_query=f"a.VICTIMALLEGEDRACE in ({combined_race})"

#     combined_fado=", ".join([f"'{element}'" for element in selected_fados])
    combined_crimes=", ".join([f"'{element}'" for element in selected_crimes])


    combined_county=", ".join([f"'{element}'" for element in selected_counties])
    
#     print(combined_county)


    query1=f"""
WITH CountyCrime AS (
    SELECT
       
        co.county,
        l.year,
        c.crime_desc,
        SUM(c.crime_count) AS total_crime_count
    FROM
        "UT.SHARMA".crime c
    JOIN
        spotukuchi.county co ON c.precinct_id = co.precinct_id
    JOIN
        spotukuchi.literacy l ON co.county = l.county AND c.year = l.year
    WHERE
        l.year BETWEEN {start_year} AND {end_year}
        AND co.county in ({combined_county})
        AND c.crime_desc in ({combined_crimes})
    GROUP BY
        co.county, l.year, c.crime_desc
)

SELECT
    cc.crime_desc,
    cc.total_crime_count,
    l.dropoutcount,
    l.dropoutrate,
    l.year,
    l.county
FROM
    CountyCrime cc
JOIN
    spotukuchi.literacy l ON cc.county = l.county AND cc.year = l.year

"""
    df = pd.read_sql(query1, connection)
    df = df.sort_values(by='YEAR')
    fig = go.Figure()

    for county in df['COUNTY'].unique():
        county_data = df[df['COUNTY'] == county]
        for crime in df['CRIME_DESC'].unique():
            crime_data = county_data[county_data['CRIME_DESC'] == crime]
            fig.add_trace(go.Scatter(
                x=crime_data['YEAR'],
                y=crime_data[f'TOTAL_CRIME_COUNT'],
                mode='lines+markers',
                name=f'{crime} in {county}',
                hovertemplate=(
                        'Year: %{x}<br>'
                        'crime:'+county+'<br>'
                        'crime:'+crime+'<br>'
                        'Count: %{y}<br>'
                        '<extra></extra>'  # Hides the trace name from the hover text
                    )               

            ))
    
    fig.update_layout(title=f'Crime Trend in NYC by county from {start_year} to {end_year}',
                      xaxis_title='Year',
                      yaxis_title='Total Crimes',
                      xaxis=dict(type='category', categoryorder='category ascending')
                      )
    


    fig_drop = go.Figure()
    for county in df['COUNTY'].unique():
        county_data = df[df['COUNTY'] == county]
        fig_drop.add_trace(go.Scatter(
                x=county_data['YEAR'],
                y=county_data[f'DROPOUTRATE'],
                mode='lines+markers',
                name=f'Dropout in {county}',
                hovertemplate=(
                        'Year: %{x}<br>'
                        'crime:'+county+'<br>'
                        'Rate: %{y}<br>'
                        '<extra></extra>'  # Hides the trace name from the hover text
                    )))
        
        fig_drop.update_layout(title=f'High School Drop out rate in {combined_county} in from {start_year} to {end_year}',
                      xaxis_title='Year',
                      yaxis_title='Dropout Rate(%)',
                      xaxis=dict(type='category', categoryorder='category ascending')
                      )


    
    graphsJSON = {
        'graph_trend': json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
        'graph_drop': json.dumps(fig_drop, cls=plotly.utils.PlotlyJSONEncoder)
        # 'allegation_chart': json.dumps(pie_fig, cls=plotly.utils.PlotlyJSONEncoder),
        # 'officer_experience_chart': json.dumps(officer_experience_pie, cls=plotly.utils.PlotlyJSONEncoder)
    }

    return graphsJSON





@app.route('/query2')
def query2():
    # Fetch unique values for years, crime types, and counties for the dropdowns
    years_query = "SELECT DISTINCT year FROM \"UT.SHARMA\".poverty ORDER BY year"
    counties_query = "SELECT DISTINCT COUNTY FROM spotukuchi.county ORDER BY COUNTY"
   


    df_years = pd.read_sql(years_query, connection)
    df_counties = pd.read_sql(counties_query, connection)
    
    years = df_years['YEAR'].tolist() if 'YEAR' in df_years.columns else []

    counties = df_counties['COUNTY'].tolist() if 'COUNTY' in df_counties.columns else []

   
    return render_template('query2.html', years=years, counties=counties)

@app.route('/update_graph_2', methods=['POST'])
def update_graph_2():
    filter_params = request.json
    selected_years = filter_params['years']
    selected_counties = filter_params['counties']
   
    # print(selected_crimes)
    # print(selected_counties)

#     selected_races=filter_params['race_types']
#     selected_age=filter_params['age_types']
    start_year = min(selected_years)
    end_year = max(selected_years)
#     # print(selected_counties)
#     # print(selected_years)
#     # print(selected_fados)
#     # print(selected_races)
#     # print(selected_age)
#     combined_race = ", ".join([f"'{element}'" for element in selected_races])
#     combined_race_query=f"a.VICTIMALLEGEDRACE in ({combined_race})"

#     combined_fado=", ".join([f"'{element}'" for element in selected_fados])
   


    combined_county=", ".join([f"'{element}'" for element in selected_counties])
    
#     print(combined_county)


    query2=f"""
WITH CrimeData AS (
    SELECT 
        c.Year,
        co.county,
        c.Crime_desc,
        SUM(c.Crime_count) AS crime_count
    FROM 
        "UT.SHARMA".crime c
    INNER JOIN 
        spotukuchi.county co ON c.Precinct_ID = co.Precinct_ID
    WHERE co.precinct_id = c.Precinct_ID
    GROUP BY 
        c.Year, co.county, c.Crime_desc
),
PovertyData AS (
    SELECT 
        Year,
        County,
        AVG(poverty_count) AS avg_poverty_count
    FROM 
        "UT.SHARMA".poverty
    GROUP BY 
        Year, County
),
CombinedData AS (
    SELECT 
        cd.Year,
        cd.county,
        cd.crime_desc,
        cd.crime_count,
        pd.avg_poverty_count
    FROM 
        CrimeData cd
    INNER JOIN 
        PovertyData pd ON cd.county = pd.county AND cd.Year = pd.Year
)
SELECT 
    Year,
    county,
    crime_desc,
    crime_count,
    AVG(avg_poverty_count) AS overall_avg_poverty_count
FROM 
    CombinedData
WHERE Year BETWEEN {start_year} AND {end_year} AND county IN ({combined_county})
GROUP BY 
    Year, county, crime_desc, crime_count
ORDER BY 
    Year
"""
    df = pd.read_sql(query2, connection)
    df = df.sort_values(by='YEAR')
    figu_pov = px.line(df, x='YEAR', y='OVERALL_AVG_POVERTY_COUNT',
               color='COUNTY',
               labels={'OVERALL_AVG_POVERTY_COUNT': 'Average Poverty Count'},
               title='Poverty Trend by County')
    
    figu_cc = px.line(df, x='YEAR', y='CRIME_COUNT',
               facet_col='COUNTY',       
               color='CRIME_DESC',
               labels={'OVERALL_AVG_POVERTY_COUNT': 'Average Poverty Count'},
               title='Poverty Trend by County')
    
    figu_pov.update_layout(title=f'Average Poverty in {combined_county} from {start_year} to {end_year}',
                      xaxis_title='Year',
                      yaxis_title='Avg Poverty',
                      xaxis=dict(type='category', categoryorder='category ascending')
                      )
    
    figu_cc.update_layout(title=f'Crime Trend in NYC from {start_year} to {end_year}',
                      xaxis_title='Year',
                      yaxis_title='Total Crimes',
                      xaxis=dict(type='category', categoryorder='category ascending')
                      )






    
    graphsJSON = {
        'graph_pov': json.dumps(figu_pov, cls=plotly.utils.PlotlyJSONEncoder),
        'graph_cc': json.dumps(figu_cc, cls=plotly.utils.PlotlyJSONEncoder)
        # 'allegation_chart': json.dumps(pie_fig, cls=plotly.utils.PlotlyJSONEncoder),
        # 'officer_experience_chart': json.dumps(officer_experience_pie, cls=plotly.utils.PlotlyJSONEncoder)
    }

    return graphsJSON

if __name__ == '__main__':
    app.run(debug=True)