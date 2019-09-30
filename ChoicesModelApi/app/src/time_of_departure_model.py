import database_connection
import pandas as pd
import biogeme.database as db
import biogeme.biogeme as bio
import biogeme.models as models
import collections
from datetime import datetime
from biogeme.expressions import *
import os


class TimeOfDeparture:
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
        if country == 'ES': country = 'GR'  # FIXME remove the workaround, once we have data for ES

        # select data from the database, for the country that is currently being estimated
        sql.run_query(sql.select_data, {
            'table_name': 'departure_time_data',
            'columns': [
                'trip_dur_earlier',
                'trip_walk_earlier',
                'trip_freq_earlier',
                'trip_dur_ontime',
                'trip_walk_ontime',
                'trip_freq_ontime',
                'trip_dur_later',
                'trip_walk_later',
                'trip_freq_later',
                'trip_discount_earlier',
                'trip_discount_later',
                'trip_discount_ontime',
                'user_gender',
                'user_imp_arr',
                'trip_purpose',
                'AGE',
                'user_income',
                'user_household',
                'user_trips_pt',
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
        pandas_df_for_specified_country.replace('Null', 0)

        return pandas_df_for_specified_country

    def evaluate_model(self, pandas_df_for_specified_country, MODEL):
        # Estimation of probabilities for each alternative on aggregate. Simulate / forecast.

        def print_mode_shares(modename, modenumber):
            seriesObj = simresults.apply(lambda x: True if x['Actual choice'] == modenumber else False, axis=1)
            REAL = len(seriesObj[seriesObj == True].index)
            seriesObj = simresults.apply(lambda x: True if x['Simulated choice'] == modenumber else False, axis=1)
            SIMU = len(seriesObj[seriesObj == True].index)
            shares = (modename, '--> Real:' + "{0:.1%}".format(REAL / simresults.shape[0]) +
                    '| Simu:' + "{0:.1%}".format(SIMU / simresults.shape[0]))
            print(shares)

        biosim = bio.BIOGEME(db.Database('estimationdb', pandas_df_for_specified_country), MODEL.structure)
        biosim.modelName = "simulated_model"
        simresults = biosim.simulate(MODEL.betas)

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
                'Rho-square': "{0:.3}".format(MODEL.results.getGeneralStatistics()['Rho-square-bar for the init. model'][0])}

    def estimate_model(self, pandas_df_for_specified_country, country):
        '''

        :param pandas_df_for_specified_country:
        :param country:
        :return: The estimated model, in a variable with 3 attributes: betas, structure, results.
        '''
        # create the respective database (needed for biogeme)
        estimationdb = db.Database('estimationdb', pandas_df_for_specified_country)

        print('Training Time of Departure model for', country)

        # Alternative Specific Constants
        ASC_EARLIER = Beta('ASC_EARLIER', 0, None, None, 1)  # This ASC remains equal to zero
        ASC_ONTIME = Beta('ASC_ONTIME', 0, None, None, 0)
        ASC_LATER = Beta('ASC_LATER', 0, None, None, 0)

        # Beta variables (i.e. coefficients) - alternative specific
        BETA_TT = Beta('BETA_TT', 0, None, None, 0)  # Travel Time - Beta of TT1, TT2, TT3 - same across all Alts
        BETA_WT = Beta('BETA_WT', 0, None, None, 0)  # Walking Time - Beta of WT1, WT2, WT3 - same across all Alts
        BETA_FREQ = Beta('BETA_FREQ', 0, None, None, 0)  # Frequency - Beta of F1, F2, F3 - same across all Alts
        BETA_FARE_DISCOUNT = Beta('BETA_FARE_DISCOUNT', 0, None, None, 0)  # Fare Discount - Beta of C1, C2, C3 - same across all Alts

        # Beta variables (i.e. coefficients) - traveller
        BETA_GENDER_ONTIME = Beta('BETA_GENDER_ONTIME', 0, None, None, 0)  # Beta of GENDER, for Alt 2
        BETA_IMPORTANT_ONTIME = Beta('BETA_IMPORTANT_ONTIME', 0, None, None, 0)  # Beta of TWORK, for Alt 2
        BETA_SCOPE_ONTIME = Beta('BETA_SCOPE_ONTIME', 0, None, None, 0)  # Beta of SCOPE, for Alt 2
        BETA_NPT_ONTIME = Beta('BETA_NPT_ONTIME', 0, None, None, 0)  # Beta of NPT, for Alt 2

        BETA_GENDER_LATER = Beta('BETA_GENDER_LATER', 0, None, None, 0)  # Beta of GENDER, for Alt 3
        BETA_IMPORTANT_LATER = Beta('BETA_IMPORTANT_LATER', 0, None, None, 0)  # Beta of TWORK, for Alt 3
        BETA_SCOPE_LATER = Beta('BETA_SCOPE_LATER', 0, None, None, 0)  # Beta of SCOPE, for Alt 3
        BETA_NPT_LATER = Beta('BETA_NPT_LATER', 0, None, None, 0)  # Beta of NPT, for Alt 3
        BETA_HOUSEHOLD_LATER = Beta('BETA_HOUSEHOLD_LATER', 0, None, None, 0)  # Beta of HOUSEHOLD, for Alt 3
        BETA_INCOME_LATER = Beta('BETA_INCOME_LATER', 0, None, None, 0)  # Beta of INCOME, for Alt 3
        BETA_AGE_LATER = Beta('BETA_AGE_LATER', 0, None, None, 0)  # Beta of AGE, for Alt 3

        AGE = Variable('AGE')
        user_income = Variable('user_income')
        user_household = Variable('user_household')
        user_trips_pt = Variable('user_trips_pt')
        trip_discount_earlier = Variable('trip_discount_earlier')
        trip_discount_later = Variable('trip_discount_later')
        trip_discount_ontime = Variable('trip_discount_ontime')
        trip_dur_earlier = Variable('trip_dur_earlier')
        trip_dur_later = Variable('trip_dur_later')
        trip_dur_ontime = Variable('trip_dur_ontime')
        trip_freq_earlier = Variable('trip_freq_earlier')
        trip_freq_later = Variable('trip_freq_later')
        trip_freq_ontime = Variable('trip_freq_ontime')
        trip_purpose = Variable('trip_purpose')
        trip_walk_earlier = Variable('trip_walk_earlier')
        trip_walk_later = Variable('trip_walk_later')
        trip_walk_ontime = Variable('trip_walk_ontime')
        user_choice = Variable('user_choice')
        user_gender = Variable('user_gender')
        user_imp_arr = Variable('user_imp_arr')

        if country == 'GR' or country == 'ES':  # FIXME create a separate model for ES
            # Definition of utility functions - one for each alternative:
            V_EARLIER = ASC_EARLIER + \
                BETA_TT * trip_dur_earlier + \
                BETA_WT * trip_walk_earlier + \
                BETA_FREQ * trip_freq_earlier

            V_ONTIME = ASC_ONTIME + \
                BETA_TT * trip_dur_ontime + \
                BETA_WT * trip_walk_ontime + \
                BETA_FREQ * trip_freq_ontime + \
                BETA_IMPORTANT_ONTIME * user_imp_arr + \
                BETA_NPT_ONTIME * user_trips_pt

            V_LATER = ASC_LATER + \
                BETA_TT * trip_dur_later + \
                BETA_WT * trip_walk_later + \
                BETA_FREQ * trip_freq_later + \
                BETA_IMPORTANT_LATER * user_imp_arr + \
                BETA_GENDER_LATER * user_gender + \
                BETA_AGE_LATER * AGE + \
                BETA_INCOME_LATER * user_income + \
                BETA_HOUSEHOLD_LATER * user_household + \
                BETA_NPT_LATER * user_trips_pt

        elif country == 'NL':
            # Definition of utility functions - one for each alternative:
            V_EARLIER = ASC_EARLIER + \
                BETA_TT * trip_dur_earlier + \
                BETA_WT * trip_walk_earlier + \
                BETA_FARE_DISCOUNT * trip_discount_earlier + \
                BETA_FREQ * trip_freq_earlier

            V_ONTIME = ASC_ONTIME + \
                BETA_TT * trip_dur_ontime + \
                BETA_WT * trip_walk_ontime + \
                BETA_FARE_DISCOUNT * trip_discount_ontime + \
                BETA_FREQ * trip_freq_ontime + \
                BETA_IMPORTANT_ONTIME * user_imp_arr + \
                BETA_GENDER_ONTIME * user_gender

            V_LATER = ASC_LATER + \
                BETA_TT * trip_dur_later + \
                BETA_WT * trip_walk_later + \
                BETA_FARE_DISCOUNT * trip_discount_later + \
                BETA_FREQ * trip_freq_later + \
                BETA_IMPORTANT_LATER * user_imp_arr + \
                BETA_GENDER_LATER * user_gender + \
                BETA_SCOPE_LATER * trip_purpose

        elif country == 'PT':
            # Definition of utility functions - one for each alternative:
            V_EARLIER = ASC_EARLIER + \
                BETA_TT * trip_dur_earlier + \
                BETA_WT * trip_walk_earlier + \
                BETA_FREQ * trip_freq_earlier

            V_ONTIME = ASC_ONTIME + \
                BETA_TT * trip_dur_ontime + \
                BETA_WT * trip_walk_ontime + \
                BETA_FREQ * trip_freq_ontime + \
                BETA_IMPORTANT_ONTIME * user_imp_arr + \
                BETA_GENDER_ONTIME * user_gender + \
                BETA_SCOPE_ONTIME * trip_purpose

            V_LATER = ASC_LATER + \
                BETA_TT * trip_dur_later + \
                BETA_WT * trip_walk_later + \
                BETA_FREQ * trip_freq_later + \
                BETA_IMPORTANT_LATER * user_imp_arr + \
                BETA_GENDER_LATER * user_gender + \
                BETA_SCOPE_LATER * trip_purpose
        else:
            V_EARLIER = ASC_EARLIER
            V_ONTIME = ASC_ONTIME
            V_LATER = ASC_LATER
            print('There is no model specification for ', country)

        # Associate utility functions with the numbering of alternatives
        V = {1: V_EARLIER,
             2: V_ONTIME,
             3: V_LATER}

        # Associate the availability conditions with the alternatives. (Does not really apply on ToD modelling)
        av = {1: 1,  # A user is able to arrive earlier..
              2: 1,  # A user is able to arrive on time..
              3: 1}  # A user is able to arrive later..

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
        #       {'Depart earlier': "{0:.1%}".format(suggestion[0]),
        #        'Depart on-time': "{0:.1%}".format(suggestion[1]),
        #        'Depart later': "{0:.1%}".format(suggestion[2]),
        #        'My-TRAC recommendation': int(suggestion[3])})

        return {'tod_earlier': suggestion[0],
                'tod_ontime': suggestion[1],
                'tod_later': suggestion[2]}


