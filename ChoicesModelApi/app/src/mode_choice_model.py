import database_connection
import pandas as pd
import biogeme.database as db
import biogeme.biogeme as bio
import biogeme.models as models
import collections
from datetime import datetime
from biogeme.expressions import *
import os


class ModeChoice:
    def __init__(self):
        return

    def __del__(self):
        try:
            self.__cleanup_after_model_training()
        except:
            pass
        return None

    def __cleanup_after_model_training(self):
        for file in os.listdir(os.getcwd()):
            if os.path.isfile(file) and file.startswith("logitEstimation"):
                # print(file, ' deleted.')  # Debug print
                os.remove(file)
        os.remove('headers.py')

    def __birthday_to_age(self, birthday):
        '''
        Takes a birthday in YYYMMDD format and returns a classification for age, ranging from 1 to 6.
        18-24	1
        25-34	2
        35-44	3
        45-54	4
        55-64	5
        ≥65	    6
        :param birthday: A string or int variable for birthday YYYYMMDD
        :return: An int from 1 to 6, representing the age category of the user
        '''
        age = (datetime.now() - datetime.strptime(str(int(birthday)), "%Y%m%d")).days / 365
        if age < 25:
            age = 1
        elif age < 35:
            age = 2
        elif age < 45:
            age = 3
        elif age < 55:
            age = 4
        elif age < 65:
            age = 5
        else:
            age = 6
        return age

    def connect_to_db(self, database_name, country):
        """
        connect to a database, for a given country. return a pandas dataframe.

        :param database_name: the name of the database
        :param country: the code of the country (i.e. gr, es, nl, pt)
        :return: a pandas db that is readable by biogeme
        """
        # connect to the database
        sql = database_connection.DatabaseConnection(database_name)
        if country == 'ES':  # FIXME remove the workaround, once we have data for ES
            country = 'GR'

        # select data from the database, for the country that is currently being estimated
        sql.run_query(sql.select_data, {
            'table_name': 'mode_choice_data',
            'columns': [
                'trip_comfort_car',
                'trip_comfort_moto',
                'trip_comfort_pt',
                'trip_cost_car',
                'trip_cost_moto',
                'trip_cost_pt',
                'trip_dur_car',
                'trip_dur_moto',
                'trip_dur_pt',
                'trip_purpose',
                'AGE',
                'user_gender',
                'user_occupation',
                'user_trips_car',
                'user_trips_pt',
                'user_car_avail',
                'user_bike_avail',
                'user_moto_avail',
                'user_choice'
            ],
            'where_cols': [
                'user_country'
            ],
            'where_values': [
                country
            ]
        })
        # store data in a pandas dataframe, readable by biogeme
        pandas_df_for_specified_country = pd.DataFrame(data=sql.output).transpose()
        return pandas_df_for_specified_country

    def evaluate_model(self, pandas_df_for_specified_country, model):
        # Estimation of probabilities for each alternative on aggregate. Simulate / forecast.

        def print_mode_shares(modename, modenumber):
            seriesObj = simresults.apply(lambda x: True if x['Actual choice'] == modenumber else False, axis=1)
            REAL = len(seriesObj[seriesObj == True].index)
            seriesObj = simresults.apply(lambda x: True if x['Simulated choice'] == modenumber else False, axis=1)
            SIMU = len(seriesObj[seriesObj == True].index)
            shares = (modename, '--> Real:' + "{0:.1%}".format(REAL / simresults.shape[0]) +
                    '| Simu:' + "{0:.1%}".format(SIMU / simresults.shape[0]))
            print(shares)

        biosim = bio.BIOGEME(db.Database('estimationdb', pandas_df_for_specified_country), model.structure)
        biosim.modelName = "simulated_model"
        simresults = biosim.simulate(model.betas)

        # Add a column containing the suggestion from the model
        simresults['Simulated choice'] = simresults.idxmax(axis=1)
        # Add a column containing the actual choice of the individual
        simresults['Actual choice'] = pandas_df_for_specified_country['user_choice'].to_numpy()
        # Add a column which compares the predicted against the RP choice (correct prediction = 1, wrong prediction = 0)
        simresults['Correct prediction'] = np.where(simresults['Simulated choice'] == simresults['Actual choice'], 1, 0)

        #print_mode_shares('Depart earlier', 1)
        #print_mode_shares('Depart on-time', 2)
        #print_mode_shares('Depart later  ', 3)

        return {'Model prediction accuracy': "{0:.1%}".format(simresults['Correct prediction'].mean()),
                'Rho-square': "{0:.3}".format(model.results.getGeneralStatistics()['Rho-square-bar for the init. model'][0])}

    def estimate_model(self, pandas_df_for_specified_country, country):
        '''
        :param pandas_df_for_specified_country:
        :param country:
        :return: The estimated model, in a variable with 3 attributes: betas, structure, results.
        '''
        mypanda = pandas_df_for_specified_country
        for i in range(1, 7):
            mypanda['OCC_' + str(i)] = np.where(pandas_df_for_specified_country['user_occupation'] == i, 1, 0)

        # create the respective database (needed for biogeme)
        estimationdb = db.Database('estimationdb', mypanda)

        print('Training Mode Choice model for', country)

        # Alternative Specific Constants
        ASC_CAR = Beta('ASC_CAR', 0, None, None, 1)  # This ASC remains equal to zero
        ASC_PT = Beta('ASC_PT', 0, None, None, 0)
        ASC_MOT = Beta('ASC_MOT', 0, None, None, 0)
        ASC_BIKE = Beta('ASC_BIKE', 0, None, None, 0)

        # Beta variables (i.e. coefficients) - alternative specific
        BETA_TIME = Beta('BETA_TIME', 0, None, None, 0)  # Travel Time
        BETA_COST = Beta('BETA_COST', 0, None, None, 0)  # Travel Cost
        BETA_S = Beta('BETA_S', 0, None, None, 0)  # Comfort

        # Beta variables (i.e. coefficients) - traveller
        BETA_AGE_PT = Beta('BETA_AGE_PT', 0, None, None, 0)  # Age
        BETA_NCAR_PT = Beta('BETA_NCAR_PT', 0, None, None, 0)  # Number of trips by car
        BETA_NPT_PT = Beta('BETA_NPT_PT', 0, None, None, 0)  # Number of trips by pt
        BETA_GENDER_PT = Beta('BETA_GENDER_PT', 0, None, None, 0)  # Gender
        BETA_SCOPE_PT = Beta('BETA_SCOPE_PT', 0, None, None, 0)  # Trip Purpose
        BETA_OCC_1_PT = Beta('BETA_OCC_1_PT', 0, None, None, 0)  # 1:Private employee
        BETA_OCC_2_PT = Beta('BETA_OCC_2_PT', 0, None, None, 0)  # 2:Public servant
        BETA_OCC_3_PT = Beta('BETA_OCC_3_PT', 0, None, None, 0)  # 3:Self-employed
        BETA_OCC_5_PT = Beta('BETA_OCC_5_PT', 0, None, None, 0)  # 5:Retired
        BETA_OCC_6_PT = Beta('BETA_OCC_6_PT', 0, None, None, 0)  # 6:Unemployed

        BETA_AGE_BIKE = Beta('BETA_AGE_BIKE', 0, None, None, 0)  # Age
        BETA_NCAR_BIKE = Beta('BETA_NCAR_BIKE', 0, None, None, 0)  # Number of trips by car
        BETA_NPT_BIKE = Beta('BETA_NPT_BIKE', 0, None, None, 0)  # Number of trips by pt
        BETA_OCC_1_BIKE = Beta('BETA_OCC_1_BIKE', 0, None, None, 0)  # 1:Private employee
        BETA_OCC_3_BIKE = Beta('BETA_OCC_3_BIKE', 0, None, None, 0)  # 3:Self-employed
        BETA_OCC_4_BIKE = Beta('BETA_OCC_4_BIKE', 0, None, None, 0)  # 4:Student
        BETA_OCC_5_BIKE = Beta('BETA_OCC_5_BIKE', 0, None, None, 0)  # 5:Retired
        BETA_OCC_6_BIKE = Beta('BETA_OCC_6_BIKE', 0, None, None, 0)  # 6:Unemployed

        BETA_AGE_MOT = Beta('BETA_AGE_MOT', 0, None, None, 0)  # Age
        BETA_GENDER_MOT = Beta('BETA_GENDER_MOT', 0, None, None, 0)  # Gender
        BETA_SCOPE_MOT = Beta('BETA_SCOPE_MOT', 0, None, None, 0)  # Scope
        BETA_NCAR_MOT = Beta('BETA_NCAR_MOT', 0, None, None, 0)  # Number of trips by car
        BETA_NPT_MOT = Beta('BETA_NPT_MOT', 0, None, None, 0)  # Number of trips by pt
        BETA_OCC_2_MOT = Beta('BETA_OCC_2_MOT', 0, None, None, 0)  # Occupation 3
        BETA_OCC_3_MOT = Beta('BETA_OCC_3_MOT', 0, None, None, 0)  # Occupation 3
        BETA_OCC_5_MOT = Beta('BETA_OCC_5_MOT', 0, None, None, 0)  # Occupation 3
        BETA_OCC_6_MOT = Beta('BETA_OCC_6_MOT', 0, None, None, 0)  # Occupation 6

        trip_comfort_car = Variable('trip_comfort_car')
        trip_comfort_moto = Variable('trip_comfort_moto')
        trip_comfort_bike = Variable('trip_comfort_moto')  # in the training dataset, both moto and bike are under the moto variable
        trip_comfort_pt = Variable('trip_comfort_pt')
        trip_cost_car = Variable('trip_cost_car')
        trip_cost_moto = Variable('trip_cost_moto')
        trip_cost_bike = Variable('trip_cost_moto')  # in the training dataset, both moto and bike are under the moto variable
        trip_cost_pt = Variable('trip_cost_pt')
        trip_dur_car = Variable('trip_dur_car')
        trip_dur_moto = Variable('trip_dur_moto')
        trip_dur_bike = Variable('trip_dur_moto')  # in the training dataset, both moto and bike are under the moto variable
        trip_dur_pt = Variable('trip_dur_pt')
        trip_purpose = Variable('trip_purpose')
        AGE = Variable('AGE')
        user_gender = Variable('user_gender')
        user_trips_car = Variable('user_trips_car')
        user_trips_pt = Variable('user_trips_pt')
        OCC_1 = Variable('OCC_1')  # 1:Private employee
        OCC_2 = Variable('OCC_2')  # 2:Public servant
        OCC_3 = Variable('OCC_3')  # 3:Self-employed
        OCC_4 = Variable('OCC_4')  # 4:Student
        OCC_5 = Variable('OCC_5')  # 5:Retired
        OCC_6 = Variable('OCC_6')  # 6:Unemployed
        user_choice = Variable('user_choice')
        user_car_avail = Variable('user_car_avail')
        user_moto_avail = Variable('user_moto_avail')
        user_bike_avail = Variable('user_bike_avail')

        if country == 'GR' or country == 'ES':  # FIXME create a separate model for ES
            ### Definition of utility functions - one for each alternative:
            V_CAR = ASC_CAR + \
                BETA_TIME * trip_dur_car + \
                BETA_S * trip_comfort_car

            V_PT = ASC_PT + \
                BETA_TIME * trip_dur_pt+ \
                BETA_S * trip_comfort_pt + \
                BETA_SCOPE_PT * trip_purpose + \
                BETA_AGE_PT * AGE + \
                BETA_GENDER_PT * user_gender + \
                BETA_NCAR_PT * user_trips_car + \
                BETA_NPT_PT * user_trips_pt + \
                BETA_OCC_2_PT * OCC_2 + \
                BETA_OCC_5_PT * OCC_5

            V_MOT = ASC_MOT + \
                BETA_TIME * trip_dur_moto + \
                BETA_S * trip_comfort_moto + \
                BETA_SCOPE_MOT * trip_purpose + \
                BETA_AGE_MOT * AGE + \
                BETA_GENDER_MOT * user_gender + \
                BETA_NCAR_MOT * user_trips_car + \
                BETA_NPT_MOT * user_trips_pt + \
                BETA_OCC_3_MOT * OCC_3 + \
                BETA_OCC_6_MOT * OCC_6

            # Associate the availability conditions with the alternatives. (Does not really apply on ToD modelling)
            av = {1: user_car_avail,
                  2: 1,
                  3: user_moto_avail}

            # Associate utility functions with the numbering of alternatives
            V = {1: V_CAR,
                 2: V_PT,
                 3: V_MOT}

        elif country == 'NL':
            ### Definition of utility functions - one for each alternative:
            V_CAR = ASC_CAR + \
                BETA_COST * trip_cost_car + \
                BETA_TIME * trip_dur_car + \
                BETA_S * trip_comfort_car

            V_PT = ASC_PT + \
                BETA_COST * trip_cost_pt + \
                BETA_TIME * trip_dur_pt + \
                BETA_S * trip_comfort_pt + \
                BETA_AGE_PT * AGE + \
                BETA_NCAR_PT * user_trips_car + \
                BETA_NPT_PT * user_trips_pt + \
                BETA_OCC_1_PT * OCC_1 + \
                BETA_OCC_3_PT * OCC_3 + \
                BETA_OCC_5_PT * OCC_5 + \
                BETA_OCC_6_PT * OCC_6

            V_BIKE = ASC_BIKE + \
                BETA_COST * trip_cost_bike + \
                BETA_TIME * trip_dur_bike + \
                BETA_S * trip_comfort_bike + \
                BETA_AGE_BIKE * AGE + \
                BETA_NCAR_BIKE * user_trips_car + \
                BETA_NPT_BIKE * user_trips_pt + \
                BETA_OCC_1_BIKE * OCC_1 + \
                BETA_OCC_3_BIKE * OCC_3 + \
                BETA_OCC_4_BIKE * OCC_4 + \
                BETA_OCC_5_BIKE * OCC_5 + \
                BETA_OCC_6_BIKE * OCC_6

            # Associate the availability conditions with the alternatives. (Does not really apply on ToD modelling)
            av = {1: user_car_avail,
                  2: 1,
                  3: user_bike_avail}

            # Associate utility functions with the numbering of alternatives
            V = {1: V_CAR,
                 2: V_PT,
                 3: V_BIKE}

        elif country == 'PT':
            ### Definition of utility functions - one for each alternative:
            V_CAR = ASC_CAR + \
                BETA_TIME * trip_dur_car + \
                BETA_COST * trip_cost_car

            V_PT = ASC_PT + \
                BETA_TIME * trip_dur_pt + \
                BETA_COST * trip_cost_pt + \
                BETA_NCAR_PT * user_trips_car + \
                BETA_NPT_PT * user_trips_pt + \
                BETA_OCC_3_PT * OCC_3

            V_MOT = ASC_MOT + \
                BETA_TIME * trip_dur_moto + \
                BETA_COST * trip_cost_moto + \
                BETA_AGE_MOT * AGE + \
                BETA_NCAR_MOT * user_trips_car + \
                BETA_NPT_MOT * user_trips_pt + \
                BETA_OCC_2_MOT * OCC_2 + \
                BETA_OCC_3_MOT * OCC_3 + \
                BETA_OCC_5_MOT * OCC_5

            # Associate the availability conditions with the alternatives. (Does not really apply on ToD modelling)
            av = {1: user_car_avail,
                  2: 1,
                  3: user_moto_avail}

            # Associate utility functions with the numbering of alternatives
            V = {1: V_CAR,
                 2: V_PT,
                 3: V_MOT}

        else:
            V = 1
            av = 1
            print('There is no model specification for ', country)

        # The choice model is a log logit, with availability conditions
        logprob = bioLogLogit(util=V, av=av, choice=user_choice)
        biogeme = bio.BIOGEME(database=estimationdb, formulas=logprob)
        biogeme.modelName = "logitEstimation"

        # Create the outputs of the estimation and store in a namedtuple (= Model)
        results = biogeme.estimate()
        betas = results.getBetaValues()  # To be used later for the simulation of the model
        structure = {1: models.logit(V, av, 1),
                     2: models.logit(V, av, 2),
                     3: models.logit(V, av, 3)}
        Output = collections.namedtuple('Output', ['betas', 'structure', 'results'])
        Model = Output(betas, structure, results)

        self.__cleanup_after_model_training()
        # print(self.evaluate_model(pandas_df_for_specified_country, Model))
        return Model

    def predict(self, trip_data, model_for_specified_country):
        for i in range(1, 7):
            trip_data['OCC_' + str(i)] = np.where(trip_data['user_occupation'] == i, 1, 0)

        trip_data['AGE'] = self.__birthday_to_age(trip_data['user_birthday'])

        # The trip is stored in a biogeme database, since it is required by Biogeme in order for it to function
        tripdb = db.Database("SuggestionDB", trip_data)

        # Simulate / forecast
        biosuggest = bio.BIOGEME(tripdb, model_for_specified_country.structure)
        biosuggest.modelName = "suggestion_to_user"
        suggestionresults = biosuggest.simulate(model_for_specified_country.betas)
        # Get the column index number of the max probability. This is My-TRAC's recommendation. Store it in a new col.
        suggestionresults['Recommendation'] = suggestionresults.idxmax(axis=1)

        suggestion = suggestionresults.values[0]

        # print('Trip data = ', trip_data.to_json())
        # print('Results = ',
        #       {'CAR': "{0:.1%}".format(suggestion[0]),
        #        'PT': "{0:.1%}".format(suggestion[1]),
        #        'BIKE/MOTO': "{0:.1%}".format(suggestion[2]),
        #        'My-TRAC recommendation': int(suggestion[3])})

        return {'mod_car': suggestion[0],
                'mod_pt': suggestion[1],
                'mod_motbike': suggestion[2]}
