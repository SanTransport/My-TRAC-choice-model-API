import mysql.connector
from aethon_API_main import dbhost, dbuser, dbpassword, dbdb

cnx = mysql.connector.connect(user=dbuser, password=dbpassword, host=dbhost, database=dbdb)
cursor = cnx.cursor()

def executeScriptsFromFile(filename):
    """Steps to import sql file via python:
    1 download and install mysql
    2. install mysql.connect(a python library)
    3. config the db user, password, database name and your sql file location
    4. execute this file `python import-sql-file-to-mysql-via-python.py`

    :param string filename: The name of the file we are importing. Shoould be "<filename>.sql
    """
    # Open and read the file as a single buffer
    fd = open(filename, 'r')
    sqlFile = fd.read()
    fd.close()

    # all SQL commands (split on ';')
    sqlCommands = sqlFile.split(';')

    # Execute every command from the input file
    for command in sqlCommands:
        # This will skip and report errors
        # For example, if the tables do not yet exist, this will skip over
        # the DROP TABLE commands
        try:
          if command.rstrip() != '':
            cursor.execute(command)
        except ValueError as msg:
            print("Command skipped: ", msg)
