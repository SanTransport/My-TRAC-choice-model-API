'''
Pretty similar to the mode/departure time choice models. Assumes a maximum of
10 itineraries. Parses the request_reply field in user_chooses_route for model
estimation. For preditcion, expects a URL describing all attributes as in below
example:
    
http://localhost:5000/choice/route/?user_country=NL
&transitTime_0=1500&transitTime_1=3000&transitTime_2=0&transitTime_3=0&transitTime_4=0&transitTime_5=0&transitTime_6=0&transitTime_7=0&transitTime_8=0&transitTime_9=0
&transfers_0=1&transfers_1=0&transfers_2=0&transfers_3=0&transfers_4=0&transfers_5=0&transfers_6=0&transfers_7=0&transfers_8=0&transfers_9=0
&waitingTime_0=1000&waitingTime_1=300&waitingTime_2=0&waitingTime_3=0&waitingTime_4=0&waitingTime_5=0&waitingTime_6=0&waitingTime_7=0&waitingTime_8=0&waitingTime_9=0
&routeAvail_0=1&routeAvail_1=1&routeAvail_2=0&routeAvail_3=0&routeAvail_4=0&routeAvail_5=0&routeAvail_6=0&routeAvail_7=0&routeAvail_8=0&routeAvail_9=0
&user_birthday=19861224&user_gender=1&user_income=1&user_traveller_type=0&user_often_pt=2&trip_id=567&mytrac_id=765

'''
import database_connection_route
import pandas as pd
import biogeme.database as db
import biogeme.biogeme as bio
import biogeme.models as models
import collections
from datetime import datetime
from biogeme.expressions import *
import os

import numpy as np
import json


class RouteChoice:
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
        sql = database_connection_route.DatabaseConnection(database_name)
        if country == 'ES':  # FIXME remove the workaround, once we have data for ES
            country = 'GR'

        # select data from the database, for the country that is currently being estimated
        sql.run_query(sql.select_data, {
            'table_name': 'user_chooses_route',
            'columns': [
                'user_id', 
                'request_reply',
                'user_choice'    
            ],
            'where_cols': [],
            'where_values': []
        })
        routeData = pd.DataFrame(data=sql.output).transpose()
        
        maxItineraries = 10 # NOTE: maxItineraries fixed to 10; will also be used for BIOGEME code in the utility definition
        # Get route attributes assuming a maximum of 10 alternatives
        transitTime = np.zeros([len(routeData),maxItineraries])
        transfers = np.zeros([len(routeData),maxItineraries])
        waitingTime = np.zeros([len(routeData),maxItineraries])
        routeAvail = np.zeros([len(routeData),maxItineraries])
        numItineraries = np.zeros([len(routeData),1],dtype=int)

        for i in range(len(routeData)):
            replyJson = json.loads(routeData['request_reply'].iloc[i])
            numItineraries[i] = len(replyJson)
            for j in range(numItineraries[i][0]):
                transitTime[i,j] = replyJson[j]['transitTime']
                transfers[i,j] = replyJson[j]['transfers']
                waitingTime[i,j] = replyJson[j]['waitingTime']
                routeAvail[i,j] = 1
        
        # Put route attributes in the same dataframe
        routeData = pd.concat([
            routeData,
            pd.DataFrame(data=numItineraries,columns=['numItineraries']),
            pd.DataFrame(data=transitTime,columns=['transitTime_'+str(i) for i in range(maxItineraries)]),
            pd.DataFrame(data=transfers,columns=['transfers_'+str(i) for i in range(maxItineraries)]),
            pd.DataFrame(data=waitingTime,columns=['waitingTime_'+str(i) for i in range(maxItineraries)]),
            pd.DataFrame(data=routeAvail,columns=['routeAvail_'+str(i) for i in range(maxItineraries)])],
            axis=1)

        routeData = routeData.loc[routeData['user_choice']!=-1] # removing replies where no user choice is available

        sql.run_query(sql.select_data, {
            'table_name': 'user',
            'columns': [
                'user_id',                
                'user_birthday',
                'user_gender', # 2 categories: male, female
                'user_income', # 3 categories: low, medium, high
                'user_often_pt', # 4 categories: never, rarely, 1-2times/week, daily
                'user_traveller_type' # 2 categories: work/edu, other
            ],
            'where_cols': [
                'user_country'
            ],
            'where_values': [
                country
            ]
        })
        userData = pd.DataFrame(data=sql.output).transpose()
        
        userData = userData.loc[(userData['user_id']!=0)&(userData['user_birthday']!=0)] # remove invalid users and users with missing information
        
        # from birthday to age
        userData['AGE'] = np.ceil(
                (
                    (
                        (datetime.now()-pd.to_datetime(userData['user_birthday'],format='%Y%m%d',errors='coerce')
                                ).dt.days/(365))-25)/10)+1
        userData.loc[userData['AGE']<1,'AGE'] = 1
        
        # store data in a pandas dataframe, readable by biogeme
        pandas_df_for_specified_country = pd.merge(routeData,userData,on='user_id') # only users of the said country will remain; others will be filtered out with this merge
        pandas_df_for_specified_country['AGE'] = pandas_df_for_specified_country['AGE'].astype(int)
        pandas_df_for_specified_country['user_id'] = pandas_df_for_specified_country['user_id'].astype(int)
        pandas_df_for_specified_country['user_choice'] = pandas_df_for_specified_country['user_choice'].astype(int)+1
        pandas_df_for_specified_country = pandas_df_for_specified_country.drop(columns=['request_reply'])
        return pandas_df_for_specified_country

    def evaluate_model(self, pandas_df_for_specified_country, model):
        # Estimation of probabilities for each alternative on aggregate. Simulate / forecast.
        def print_route_shares(routename, routenumber):
            seriesObj = simresults.apply(lambda x: True if x['Actual choice'] == routenumber else False, axis=1)
            REAL = len(seriesObj[seriesObj == True].index)
            seriesObj = simresults.apply(lambda x: True if x['Simulated choice'] == routenumber else False, axis=1)
            SIMU = len(seriesObj[seriesObj == True].index)
            shares = (routename, '--> Real:' + "{0:.1%}".format(REAL / simresults.shape[0]) +
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

        return {'Model prediction accuracy': "{0:.1%}".format(simresults['Correct prediction'].mean()),
                'Rho-square': "{0:.3}".format(model.results.getGeneralStatistics()['Rho-square-bar for the init. model'][0])}

    def estimate_model(self, pandas_df_for_specified_country, country):
        '''
        :param pandas_df_for_specified_country:
        :param country:
        :return: The estimated model, in a variable with 3 attributes: betas, structure, results.
        '''
        mypanda = pandas_df_for_specified_country
        
        # create the respective database (needed for biogeme)
        estimationdb = db.Database('estimationdb', mypanda)

        print('Training Route Choice model for', country)
        # NOTE: max number of itineraries fixed to 10
        # Beta variables (i.e. coefficients) - alternative specific
        bTotalIvt = Beta('bTotalIvt',0,-1000,1000,0) # transitTime in OTP reply
        bTransfers	= Beta('bTransfers',0,-1000,1000,0) # transfers in OTP reply
        bTotalWt = Beta('bTotalWt',0,-1000,1000,0) # waitingTime in OTP reply
        
        # Beta variables (i.e. coefficients) - traveller
        bAge = Beta('bAge',0,-1000,1000,0)  # Age
        bTrFreq = Beta('bTrFreq',0,-1000,1000,0)  # PT trip frequency
        bGender2 = Beta('bGender2',0,-1000,1000,0)  # Gender: female
        bPurp2 = Beta('bPurp2',0,-1000,1000,0) # trip purpose: others (non-commuting)
        bNetInc1 = Beta('bNetInc1',0,-1000,1000,0) # income level: low
        bNetInc3 = Beta('bNetInc3',0,-1000,1000,0) # income level: high
        
        # Variables: choice situation
        transitTime_0 = Variable('transitTime_0')
        transitTime_1 = Variable('transitTime_1')
        transitTime_2 = Variable('transitTime_2')
        transitTime_3 = Variable('transitTime_3')
        transitTime_4 = Variable('transitTime_4')
        transitTime_5 = Variable('transitTime_5')
        transitTime_6 = Variable('transitTime_6')
        transitTime_7 = Variable('transitTime_7')
        transitTime_8 = Variable('transitTime_8')
        transitTime_9 = Variable('transitTime_9')
        
        transfers_0 = Variable('transfers_0')
        transfers_1 = Variable('transfers_1')
        transfers_2 = Variable('transfers_2')
        transfers_3 = Variable('transfers_3')
        transfers_4 = Variable('transfers_4')
        transfers_5 = Variable('transfers_5')
        transfers_6 = Variable('transfers_6')
        transfers_7 = Variable('transfers_7')
        transfers_8 = Variable('transfers_8')
        transfers_9 = Variable('transfers_9')

        waitingTime_0 = Variable('waitingTime_0')
        waitingTime_1 = Variable('waitingTime_1')
        waitingTime_2 = Variable('waitingTime_2')
        waitingTime_3 = Variable('waitingTime_3')
        waitingTime_4 = Variable('waitingTime_4')
        waitingTime_5 = Variable('waitingTime_5')
        waitingTime_6 = Variable('waitingTime_6')
        waitingTime_7 = Variable('waitingTime_7')
        waitingTime_8 = Variable('waitingTime_8')
        waitingTime_9 = Variable('waitingTime_9')

        # Variables: alternative availability
        routeAvail_0 = Variable('routeAvail_0')
        routeAvail_1 = Variable('routeAvail_1')
        routeAvail_2 = Variable('routeAvail_2')
        routeAvail_3 = Variable('routeAvail_3')
        routeAvail_4 = Variable('routeAvail_4')
        routeAvail_5 = Variable('routeAvail_5')
        routeAvail_6 = Variable('routeAvail_6')
        routeAvail_7 = Variable('routeAvail_7')
        routeAvail_8 = Variable('routeAvail_8')
        routeAvail_9 = Variable('routeAvail_9')
        
        # Variables: personal 
        # NOTE: Currently unused!!!
        # Personal variables may be used when there is reasonable intuition
        # that different socio-demographics will consider an attribute differently
        user_traveller_type = Variable('user_traveller_type')
        AGE = Variable('AGE')
        user_gender = Variable('user_gender')
        user_often_pt = Variable('user_often_pt')
        user_income = Variable('user_income')
        
        user_choice = Variable('user_choice')
        

        if country == 'GR' or country == 'ES':  # FIXME create a separate model for ES
            ### Definition of utility functions - one for each alternative:
            V_0 = bTotalIvt * transitTime_0 + \
                bTransfers * transfers_0 + \
                bTotalWt * waitingTime_0

            V_1 = bTotalIvt * transitTime_1 + \
                bTransfers * transfers_1 + \
                bTotalWt * waitingTime_1

            V_2 = bTotalIvt * transitTime_2 + \
                bTransfers * transfers_2 + \
                bTotalWt * waitingTime_2

            V_3 = bTotalIvt * transitTime_3 + \
                bTransfers * transfers_3 + \
                bTotalWt * waitingTime_3

            V_4 = bTotalIvt * transitTime_4 + \
                bTransfers * transfers_4 + \
                bTotalWt * waitingTime_4

            V_5 = bTotalIvt * transitTime_5 + \
                bTransfers * transfers_5 + \
                bTotalWt * waitingTime_5

            V_6 = bTotalIvt * transitTime_6 + \
                bTransfers * transfers_6 + \
                bTotalWt * waitingTime_6

            V_7 = bTotalIvt * transitTime_7 + \
                bTransfers * transfers_7 + \
                bTotalWt * waitingTime_7

            V_8 = bTotalIvt * transitTime_8 + \
                bTransfers * transfers_8 + \
                bTotalWt * waitingTime_8

            V_9 = bTotalIvt * transitTime_9 + \
                bTransfers * transfers_9 + \
                bTotalWt * waitingTime_9

            # Associate the availability conditions with the alternatives. (Does not really apply on ToD modelling)
            av = {1: routeAvail_0,
                  2: routeAvail_1,
                  3: routeAvail_2,
                  4: routeAvail_3,
                  5: routeAvail_4,
                  6: routeAvail_5,
                  7: routeAvail_6,
                  8: routeAvail_7,
                  9: routeAvail_8,
                  10: routeAvail_9}

            # Associate utility functions with the numbering of alternatives
            V = {1: V_0,
                 2: V_1,
                 3: V_2,
                 4: V_3,
                 5: V_4,
                 6: V_5,
                 7: V_6,
                 8: V_7,
                 9: V_8,
                 10: V_9,
                 }

        elif country == 'NL':
            ### Definition of utility functions - one for each alternative:
            V_0 = bTotalIvt * transitTime_0 + \
                bTransfers * transfers_0 + \
                bTotalWt * waitingTime_0

            V_1 = bTotalIvt * transitTime_1 + \
                bTransfers * transfers_1 + \
                bTotalWt * waitingTime_1

            V_2 = bTotalIvt * transitTime_2 + \
                bTransfers * transfers_2 + \
                bTotalWt * waitingTime_2

            V_3 = bTotalIvt * transitTime_3 + \
                bTransfers * transfers_3 + \
                bTotalWt * waitingTime_3

            V_4 = bTotalIvt * transitTime_4 + \
                bTransfers * transfers_4 + \
                bTotalWt * waitingTime_4

            V_5 = bTotalIvt * transitTime_5 + \
                bTransfers * transfers_5 + \
                bTotalWt * waitingTime_5

            V_6 = bTotalIvt * transitTime_6 + \
                bTransfers * transfers_6 + \
                bTotalWt * waitingTime_6

            V_7 = bTotalIvt * transitTime_7 + \
                bTransfers * transfers_7 + \
                bTotalWt * waitingTime_7

            V_8 = bTotalIvt * transitTime_8 + \
                bTransfers * transfers_8 + \
                bTotalWt * waitingTime_8

            V_9 = bTotalIvt * transitTime_9 + \
                bTransfers * transfers_9 + \
                bTotalWt * waitingTime_9

            # Associate the availability conditions with the alternatives. (Does not really apply on ToD modelling)
            av = {1: routeAvail_0,
                  2: routeAvail_1,
                  3: routeAvail_2,
                  4: routeAvail_3,
                  5: routeAvail_4,
                  6: routeAvail_5,
                  7: routeAvail_6,
                  8: routeAvail_7,
                  9: routeAvail_8,
                  10: routeAvail_9}

            # Associate utility functions with the numbering of alternatives
            V = {1: V_0,
                 2: V_1,
                 3: V_2,
                 4: V_3,
                 5: V_4,
                 6: V_5,
                 7: V_6,
                 8: V_7,
                 9: V_8,
                 10: V_9,
                 }

        elif country == 'PT':
            ### Definition of utility functions - one for each alternative:
            V_0 = bTotalIvt * transitTime_0 + \
                bTransfers * transfers_0 + \
                bTotalWt * waitingTime_0

            V_1 = bTotalIvt * transitTime_1 + \
                bTransfers * transfers_1 + \
                bTotalWt * waitingTime_1

            V_2 = bTotalIvt * transitTime_2 + \
                bTransfers * transfers_2 + \
                bTotalWt * waitingTime_2

            V_3 = bTotalIvt * transitTime_3 + \
                bTransfers * transfers_3 + \
                bTotalWt * waitingTime_3

            V_4 = bTotalIvt * transitTime_4 + \
                bTransfers * transfers_4 + \
                bTotalWt * waitingTime_4

            V_5 = bTotalIvt * transitTime_5 + \
                bTransfers * transfers_5 + \
                bTotalWt * waitingTime_5

            V_6 = bTotalIvt * transitTime_6 + \
                bTransfers * transfers_6 + \
                bTotalWt * waitingTime_6

            V_7 = bTotalIvt * transitTime_7 + \
                bTransfers * transfers_7 + \
                bTotalWt * waitingTime_7

            V_8 = bTotalIvt * transitTime_8 + \
                bTransfers * transfers_8 + \
                bTotalWt * waitingTime_8

            V_9 = bTotalIvt * transitTime_9 + \
                bTransfers * transfers_9 + \
                bTotalWt * waitingTime_9

            # Associate the availability conditions with the alternatives. (Does not really apply on ToD modelling)
            av = {1: routeAvail_0,
                  2: routeAvail_1,
                  3: routeAvail_2,
                  4: routeAvail_3,
                  5: routeAvail_4,
                  6: routeAvail_5,
                  7: routeAvail_6,
                  8: routeAvail_7,
                  9: routeAvail_8,
                  10: routeAvail_9}

            # Associate utility functions with the numbering of alternatives
            V = {1: V_0,
                 2: V_1,
                 3: V_2,
                 4: V_3,
                 5: V_4,
                 6: V_5,
                 7: V_6,
                 8: V_7,
                 9: V_8,
                 10: V_9,
                 }

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
                     3: models.logit(V, av, 3),
                     4: models.logit(V, av, 4),
                     5: models.logit(V, av, 5),
                     6: models.logit(V, av, 6),
                     7: models.logit(V, av, 7),
                     8: models.logit(V, av, 8),
                     9: models.logit(V, av, 9),
                     10: models.logit(V, av, 10)}
        Output = collections.namedtuple('Output', ['betas', 'structure', 'results'])
        Model = Output(betas, structure, results)

        self.__cleanup_after_model_training()
        # print(self.evaluate_model(pandas_df_for_specified_country, Model))
        return Model

    def predict(self, trip_data, model_for_specified_country):
        #FIXME: check
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

        
        return {'route_0': suggestion[0],
                'route_1': suggestion[1],
                'route_2': suggestion[2],
                'route_3': suggestion[3],
                'route_4': suggestion[4],
                'route_5': suggestion[5],
                'route_6': suggestion[6],
                'route_7': suggestion[7],
                'route_8': suggestion[8],
                'route_9': suggestion[9],
                }