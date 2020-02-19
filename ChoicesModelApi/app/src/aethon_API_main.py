from flask import Flask, request, jsonify
import database_connection
import pandas as pd
import time
import time_of_departure_model  # Import the Time of Departure main Class
import mode_choice_model  # Import the Mode Choice main Class
import route_choice_model # Import the Route Choice main Class
TOD = time_of_departure_model.TimeOfDeparture()  # Create an instance of the Class.
MOD = mode_choice_model.ModeChoice()  # Create an instance of the Class.
ROU = route_choice_model.RouteChoice() # Create an instance of the Class.

app = Flask(__name__)

# Init Variables
#dbhost = 'localhost'  # Fixme change to 'db' when in operational environment
#dbuser = 'root'
#dbpassword = 'sanmay'
dbdb = 'mytrac_model_module'

#route_dbhost = '35.189.241.175'
#route_dbuser = 'delft'
#route_dbpassword = 'X7iK3wNQ'
route_dbdb = 'mytraclastshare'

# Create a Model class to store all models inside it
class Model:
    pass


MODEL_TOD = Model()  # the MODEL_TOD variable will have an attribute for each country
MODEL_MOD = Model()  # the MODEL_MOD variable will have an attribute for each country
MODEL_ROU = Model()  # the MODEL_ROU variable will have an attribute for each country


def __recommend(model_type):
    '''
    Read the arguments from the My-TRAC app within the URL query.
    All needed variables need to be present in the query, following the data model of My-TRAC and the model
    specification of the choice modelling (D2.3).
    As soon as the query is received, it is stored in a single-line pandas dataframe, compatible with biogeme.
    The 'predict' function is called and the recommendation is produced.
    Requirement: The model for the given country code needs to have been estimated in advance at least once.
    :return: Prediction= 1:X%, 2:Y%, 3:Z%
    '''

    args_dict = request.args.to_dict()  # store all arguments in a dictionary
    
    if (model_type=='TOD') | (model_type=='MOD'):
        # Store input query (trip) in the database
        try:
            DC = database_connection.DatabaseConnection(database_name='mytrac_model_module')
            DC.run_query(DC.insert_data, {
                'table_name': model_type.lower()+'_requests',
                'columns': list(args_dict.keys()),
                'data': list(args_dict.values())
            })
        except:
            print('Was not able to store the query into ', model_type.lower()+'_requests')
            pass

    if model_type == 'TOD':
        model = MODEL_TOD
        lib = TOD
    elif model_type == 'MOD':
        model = MODEL_MOD
        lib = MOD
    elif model_type == 'ROU':
        model = MODEL_ROU
        lib = ROU
    else:
        model = None
        lib = None

    user_country = request.args.get('user_country')  # store 'user_country' to call the appropriate model

    # parse input
    for keys in list(args_dict):
        try:
            args_dict[keys] = float(args_dict[keys])  # convert all arguments from string to float
        except ValueError:
            del args_dict[keys]  # drop variables with strings since they will later cause problems in biogeme

    sample_trip_data = pd.DataFrame(args_dict, index=[0])  # Store the dict into a pandas dataframe

    try:
        getattr(model, user_country)  # Check if the model for that country code exists
    except:
        prediction = f'The model of {user_country} has not been trained yet'  # If the model doesn't exist, catch exception
    else:
        prediction = lib.predict(sample_trip_data, getattr(model, user_country))  # Produce the recommendation.

    return jsonify(prediction)  # Return the recommendation to the My-TRAC app


@app.route("/choice/time-of-departure/")
def tod_choice_predict():
    return __recommend('TOD')

@app.route("/choice/mode/")
def mode_choice():
    return __recommend('MOD')

@app.route("/choice/route/")
def route_choice():
    return __recommend('ROU')


@app.route("/choice/time-of-departure/estimate/")
def tod_choice_estimate():
    '''
    Function that estimates (aka trains) the model for the given country.
    The country for which the model is to be estimated is passed through the URL query.
    For example: ./choice/time-of-departure/estimate/?user_country=ES
    Note, the models have to be estimated AT LEAST ONCE, before they can be used.
    The initial training of the models is performed automatically early on, as soon as the main script is initiated.
    The model is stored as an attribute within the MODEL variable, for example: MODEL_TOD.GR, MODEL_TOD.NL, etc.
    :return: A JSON diagnostic response: { Status : Message }
    '''
    arg_country = request.args.get('user_country')  # parse arguments and get the country as input
    try:
        setattr(MODEL_TOD, arg_country, TOD.estimate_model(TOD.connect_to_db(dbdb, arg_country), arg_country))
        result = {'SUCCESS': f'The Time of Departure Model of {arg_country} has been successfully estimated.'}
    except:
        result = {'FAIL': f'There is no Time of Departure Model for {arg_country}. Try (?user_country=XX, where XX=ES,GR,NL,PT)'}
    return jsonify(result)


@app.route("/choice/mode/estimate/")
def mode_choice_estimate():
    '''
    Function that estimates (aka trains) the model for the given country.
    The country for which the model is to be estimated is passed through the URL query.
    For example: ./choice/time-of-departure/estimate/?user_country=ES
    Note, the models have to be estimated AT LEAST ONCE, before they can be used.
    The initial training of the models is performed automatically early on, as soon as the main script is initiated.
    The model is stored as an attribute within the MODEL variable, for example: MODEL_MOD.GR, MODEL_MOD.NL, etc.
    :return: A JSON diagnostic response: { Status : Message }
    '''
    arg_country = request.args.get('user_country')  # parse arguments and get the country as input
    try:
        setattr(MODEL_MOD, arg_country, MOD.estimate_model(MOD.connect_to_db(dbdb, arg_country), arg_country))
        result = {'SUCCESS': f'The Mode Choice Model of {arg_country} has been successfully estimated.'}
    except:
        result = {'FAIL': f'There is no Mode Choice Model for {arg_country}. Try ?user_country=XX, where XX=ES,GR,NL,PT.'}
    return jsonify(result)


@app.route("/choice/route/estimate/")
def route_choice_estimate():
    '''
    Function that estimates (aka trains) the model for the given country.
    The country for which the model is to be estimated is passed through the URL query.
    For example: ./choice/time-of-departure/estimate/?user_country=ES
    Note, the models have to be estimated AT LEAST ONCE, before they can be used.
    The initial training of the models is performed automatically early on, as soon as the main script is initiated.
    The model is stored as an attribute within the MODEL variable, for example: MODEL_MOD.GR, MODEL_MOD.NL, etc.
    :return: A JSON diagnostic response: { Status : Message }
    '''
    arg_country = request.args.get('user_country')  # parse arguments and get the country as input
    try:
        setattr(MODEL_ROU, arg_country, ROU.estimate_model(ROU.connect_to_db(route_dbdb, arg_country), arg_country))
        result = {'SUCCESS': f'The Route Choice Model of {arg_country} has been successfully estimated.'}
    except:
        result = {'FAIL': f'There is no Route Choice Model for {arg_country}. Try ?user_country=XX, where XX=ES,GR,NL,PT. It is also possible that there is no data available for the defined country'}
    return jsonify(result)

@app.route("/")
def tod_choice_root():
    return jsonify("Status: OK")

@app.route("/choice/help/")
def tod_choice_help():
    help_tip = {'Choice Model API status': 'OK'}
    return jsonify(help_tip)
#gdgfd
#%% Main
if __name__ == "__main__":
    '''
    Train all models and store them in MODEL_TOD, MODEL_MOD, and MODEL_ROU.
    Then start the API service at 0.0.0.0.
    '''
    # First time run should be that the database is empty
    time.sleep(10)
    con = database_connection.DatabaseConnection(dbdb)
    res = con.run_query(con.select_data, {
        'table_name': 'departure_time_data',
        'columns': ["*"],
        'where_cols': ['ID'],
        'where_values': [1]
    })

    # if the database is empty indeed, then proceed to import the .sql file
    if con.output is None:
        print('Database has no data. Installing from the .sql file.')
        import install_databases
        install_databases.executeScriptsFromFile('./mytrac_model_module.sql')
        install_databases.cnx.commit()
        print('Database installed successfully from \'mytrac_model_module.sql\'')
    else:
        print('Database', dbdb, 'exists and in not-empty. Proceeding to the estimation (aka training) of the models.')

    for country in ['GR', 'PT', 'NL', 'ES']:
        setattr(MODEL_TOD, country, TOD.estimate_model(TOD.connect_to_db(dbdb, country), country))
        # print('Time of Departure BETAS for country: ', country)
        # for beta, value in getattr(MODEL_TOD, country).betas.items():
        #     print(beta, "\t%.3f" % value)

        setattr(MODEL_MOD, country, MOD.estimate_model(MOD.connect_to_db(dbdb, country), country))
        # print('Mode Choice BETAS for country: ', country)
        # for beta, value in getattr(MODEL_MOD, country).betas.items():
        #     print(beta, "\t%.3f" % value)

        try:
            setattr(MODEL_ROU, country, ROU.estimate_model(ROU.connect_to_db(route_dbdb, country), country))
        except:
            print('There is no data for a Route Choice Model in ' + country)
        # print('Route Choice BETAS for country: ', country)
        # for beta, value in getattr(MODEL_ROU, country).betas.items():
        #     print(beta, "\t%.3f" % value)

    app.run(host='0.0.0.0')
    