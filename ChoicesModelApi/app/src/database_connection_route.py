import mysql.connector
from mysql.connector import Error
#from aethon_API_main import route_dbhost, route_dbuser, route_dbpassword

route_dbhost = '35.189.241.175'
route_dbuser = 'delft'
route_dbpassword = 'X7iK3wNQ'
route_dbdb = 'mytraclastshare'


class DatabaseConnection:
    def __init__(self, database_name, host=route_dbhost, user=route_dbuser, password=route_dbpassword):
        """The class for connecting and running operations on a MySQL database.
        :param string database_name: Is the name of the database we are connecting to
        :param string host: Is the name of the database's host
        :param string user: Is the name of the user that is connecting to the database (login name)
        :param string password: Is the password for connecting to the database (login password)
        """
        self.host = host
        self.user = user
        self.password = password
        self.database_name = database_name

        # Test the connection
        self.__connect()

        # Create the output, which is returned in SELECT queries
        self.output = None

        # If not successful, we delete the class
        if not self.connection.is_connected():
            del self
            exit()


    def __del__(self):
        """On delete, we close the connection"""
        self.__disconnect()
        # REMOVED print('Disconnected from MySQL database')


    def __connect(self):
        """The function for creating the connection to the database."""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                passwd=self.password,
                database=self.database_name)

            self.cursor = self.connection.cursor()  # we need the "cursor" to execute a query. See here: https://dev.mysql.com/doc/connector-python/en/connector-python-examples.html

        except Error as error:
            print('An error occurred while connecting to MySQL: ', error)

        except:
            print('Unknown error occurred')

        else:
            None
            # REMOVED print('Connected to MySQL database')


    def __disconnect(self):
        """Use to close the connection to the db"""
        if self.cursor in locals():
            self.cursor.close()

        self.connection.close()


    def run_query(self, query_to_execute, arguments):
        """The function for running a query. The query is inserted as a function (use the class' functions as input
        depending on what you want to do, e.g., insert data or get data)
        :param callable query_to_execute: A query, as defined in this variable, is executed
        :param dict or string arguments: Dict_The arguments for running the query should contain the inputs per the function inserted in query_to_execute / String_The string of a custom query
        """
        self.output = None      # Delete the previous output (if any)

        try:
            # First, we check the inputs
            if not callable(query_to_execute):
                raise TypeError('The query to execute must be a function. See DatabaseConnection functions')

            if type(arguments) is not str and type(arguments) is not dict:
                raise TypeError('Arguments are expected as dict for insert/update/select data or string for a custom query')

            # Then, we create the input as expected by the cursor and depending on what user requested
            query_to_execute(arguments)

            # Finally, we determine whether we need to parse the data for two cases: one, if it's a custom query or of if not
            if (type(arguments) is dict):
                is_select_query = True if 'select' in query_to_execute.__name__ else False
            else:
                is_select_query = True if 'select' in arguments.lower() else False  # we are doing lower to nullify case sensitivity


            if is_select_query:
                self.output = self.__parse_selection(arguments)
            else:
                self.connection.commit()  # We need to commit when storing data only



        except ValueError as error:
            print(error.args[0], 'in function', error.args[1])

        except TypeError as error:
            print(error)

        except Error as error:
            print(error)

        except:
            print('Unknown error occurred')

        else:
            None
            # REMOVED print('Query was executed successfully')


    def custom_query(self, query):
        """A function that executes a custom query immediately without performing any parsing
        :param string query: The query to execute
        :return: none
        """
        self.cursor.execute(query)  # We execute the query immediately


    def insert_data(self, arguments):
        """This function is used to insert data in a table. It creates the input for the cursor.execute function by manipulating the arguments and then executes the query.
        For more info on operations of the function, see here: https://dev.mysql.com/doc/connector-python/en/connector-python-example-cursor-transaction.html
        :param dict arguments: The arguments for running the query. Arguments here are: table_name / columns / data. Check create_template_arguments for more info
        :return: none
        """
        # Initially, we check that the size of columns and data is the same
        if len(arguments['columns']) != len(arguments['data']) and type(arguments['data']) is not tuple and type(arguments['data']) is not list:
            raise ValueError('Size of data objects and MySQL columns do not match', 'insert_data')

        # First, we determine the query arguments which are the column names and the regexps for the values
        column_names = ', '.join(arguments['columns'])
        number_of_values = ('%s, ' * len(arguments['columns']))[0:-2]    # We are doing -2 to remove the last substring (', ')

        # Then, we create the query not including the data
        add_row = ('INSERT INTO ' + arguments['table_name'] + ' (' + column_names + ') VALUES (' + number_of_values + ')')

        # Second, we create the variable that will hold the data
        add_data = self.__format_data_for_query(arguments['data'])

        if type(arguments['data'][0]) is list or type(arguments['data'][0]) is tuple:   # Then we have many rows of data
            self.cursor.executemany(add_row, add_data)
        else:
            self.cursor.execute(add_row, add_data)


    def update_row(self, arguments):
        """This function is used to update a single row in a table. It creates the input for the cursor.execute function by manipulating the arguments and
        executes the query. Best use the primary key for the where clause. For more info on operations of the function, see here: http://www.mysqltutorial.org/python-mysql-update/
        :param dict arguments: The arguments for running the query. Arguments here are: table_name / columns / data / where_cols / where_values. Check create_template_arguments for more info
        :return: none
        """
        # Initially, we check that the size of columns and data is the same
        if len(arguments['columns']) != len(arguments['data']):
            raise ValueError('Size of data objects and MySQL columns do not match', 'insert_data')

        # First, we create the SET clause
        set_clause = 'SET ' + '=%s,'.join(arguments['columns']) + "=%s"

        # Next, we create the WHERE clause
        where_clause = self.__create_where_clause(arguments)

        # Then, we create the query
        update_row =('UPDATE ' + arguments['table_name'] + ' ' + set_clause + ' ' + where_clause)

        # Second, we create the variable that will hold the data
        update_data = self.__format_data_for_query(arguments['data'])

        # Finally, we execute the query
        self.cursor.execute(update_row, update_data)


    def select_data(self, arguments):
        """This function is used for selecting a single row and return the data specified in arguments input (columns). It creates the input for the
        cursor.execute function by manipulating the arguments and executes the query.
        :param dict arguments: The arguments for running the query. Arguments here are: table_name / columns / where_cols / where_values. Check create_template_arguments for more info
        :return: none (output is stored in class variable output)
        """
        # First, we create the SELECT part of the query
        select_expression = ', '.join(arguments['columns'])

        # Next, we create the WHERE clause
        where_clause = self.__create_where_clause(arguments, True)

        # Then, we create the query
        select_data = ('SELECT ' + select_expression + ' FROM ' + arguments['table_name'] + ' ' + where_clause)

        # Second, we create the variable that will hold the data
        where_expressions = self.__format_data_for_query(arguments['where_values'])

        # Finally, we execute the query
        self.cursor.execute(select_data, where_expressions)


    def __parse_selection(self, arguments):
        """Creates a dictionary that holds the data returned for SELECT queries. The keys are column names as they appear in the db
        :param dict arguments: The arguments for running the query and that was used in the select function
        :return dict: The output contains the column names (keys) and the data from the db (values)
        """
        # Create the output
        output = dict()

        # Fetch the data
        data = self.cursor.fetchall()

        # Get column names if the columns entry is '*'
        columns = []
        for col in self.cursor.description:
            columns.append(col[0])

        for j, row in enumerate(data):
            output[j] = dict()
            for i, entry in enumerate(columns):
                output[j][entry] = row[i]

        return output


    def __format_data_for_query(self, data):
        """Format the data as expected by the cursor
        :param list/tuple data: The data to be stored in the db
        :return tuple: The data in tuple as expected by the cursor
        """
        add_data = []
        if len(data)==0:
            add_data=data
        elif type(data[0]) is list or type(data[0]) is tuple:     # That means we have multiple rows
            if type(data[0]) is tuple and type(data) is list:   # In this case, we do not need to do any action since list(tuple()) is expected by the cursor
                add_data = data
            else:           # Then we need to prepare the data in the list(tuple()) format
                len_arguments_data = len(data)

                for i in range(0, len_arguments_data):
                    add_data.append(tuple(data[i]))

        else:   # Then we have only one row of data
            add_data = tuple(data)

        return add_data


    def __create_where_clause(self, arguments, force_variable = False):
        """Used for creating the where clause from the arguments input
        :param dict arguments: The arguments for running the query that were given by the user
        :return string: The where clause as a string
        """
        where_clause = 'WHERE '
        if (len(arguments['where_cols']) == 0):
            where_clause = ''
        elif (len(arguments['where_cols']) == 1):
            where_clause += arguments['where_cols'][0] + '=' + ('%s' if force_variable else arguments['where_values'][0])
        else:
            where_cols_len = len(arguments['where_cols'])
            for i in range(0, where_cols_len):
                where_clause += arguments['where_cols'][i] + '=' + ('%s' if force_variable else arguments['where_values'][i])

                if i != where_cols_len - 1:
                    where_clause += ' AND '

        if arguments['table_name'] == 'products_data':
            where_clause += ' AND ' + 'deleted = 0' + ' AND ' + 'approved = 1'

        return where_clause

    def create_template_arguments(self):
        """The function returns the arguments variable that is used in all functions that create the queries (e.g., see
        insert_data). Use it to obtain the input in the form expected by the functions
        Important:
        1. columns and data need to correspond (column 1 -> data 1, column 2-> data 2 etc.)
        2. if inserting data, the equivalent function can insert many rows in the table. To do that, you will need to
           insert many lists in the data list. E.g., 'data': [[data 1.1, data 1.2], [data 2.1, data 2.2]] will insert
           two lines in the table.
        :return dict: An empty arguments variable that is input for query creation functions of the class
        """
        arguments = {
            'table_name': '',   # String    / Is the table name in the db                               / Mandatory
            'columns': [],      # List      / Are the columns we updating/selecting/inserting           / Mandatory
            'data': [],         # List      / Are the data we are inserting/updating                    / Used for inserting and updating queries
            'where_cols': [],   # List      / Are the columns for the where clause (e.g., id_entry)     / Used for updating and selecting queries
            'where_values': []  # List      / Are the expressions of the where clause                   / Used for updating and selecting queries
        }

        return arguments