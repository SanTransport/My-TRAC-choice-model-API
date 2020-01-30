# Use an official Python runtime as an image
FROM python:3.7

# The EXPOSE instruction indicates the ports on which a container will listen for connections
# Since Flask apps listens to port 5000  by default, we expose it
EXPOSE 5000

# Sets the working directory for following COPY and CMD instructions
# Notice we haven’t created a directory by this name - this
# instruction creates a directory with this name if it doesn’t exist
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY src/requirements.txt /app/

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN pip3 install biogeme==3.1.2

COPY src/aethon_API_main.py /app
COPY src/database_connection.py /app
COPY src/install_databases.py /app
COPY src/mode_choice_model.py /app
COPY src/time_of_departure_model.py /app
COPY src/route_choice_model.py /app
COPY src/mytrac_model_module.sql /app

CMD python -u aethon_API_main.py
