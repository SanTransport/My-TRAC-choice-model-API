# My-TRAC-choice-model-API

Breakdown of the various variables of the query string:

-http://<ip_of_the_api>:5000/choice/mode/?
-user_country=	{ES, GR, NL, PT}	e.g.: NL
-trip_dur_car=	{from OTP: trip duration by car (in minutes)}	e.g.: 20
-trip_dur_pt=	{from OTP: trip duration by pt (in minutes)}	e.g.: 45
-trip_dur_moto=	{from OTP: trip duration by moto or bike (in minutes)}	e.g.: 15
-trip_dur_bike**=	{from OTP: trip duration by moto or bike (in minutes)}	e.g.: 30
-trip_comfort_car=	{0, 1}	e.g.: 1
-trip_comfort_pt=	{0, 1}	e.g.: 0
-trip_comfort_moto=	{0, 1}	e.g.: 1
-trip_comfort_bike**=	{0, 1}	e.g.: 1
-trip_cost_car=		{cost of using car, as a function of distance}	e.g.: 5
-trip_cost_moto=	{cost of using motorbike, as a function of distance}	e.g.: 2
-trip_cost_bike**=	{cost of using bike, always equal to 0}	e.g.: 0
-trip_cost_pt=		{cost of using pt, ticket cost}	e.g.: 1.5
-trip_purpose=	{0, 1}	e.g.: 0  * user_traveller_type
-user_birthday=	{YYYYMMDD}	e.g.: 19861224
-user_gender=	{0, 1}	e.g.: 1
-user_occupation=	{1,2,3,4,5,6}	e.g.: 3
-user_trips_car=	{1,2,3,4}	e.g.: 4  * user_often_car
-user_trips_pt=	{1,2,3,4}	e.g.: 2  * user_often_pt
-user_car_avail=	{0, 1}	e.g.: 1
-user_bike_avail=	{0, 1}	e.g.: 1
-user_moto_avail=	{0, 1}	e.g.: 1
-trip_id=		{string} 	e.g.: 567
-mytrac_id=	{long}		e.g.: 765

** for the NL model, use the _bike variables instead of the _moto variables.

The model may be queried at http://35.190.118.92/choice/help/

The docker can be found here: https://hub.docker.com/r/mytrac/choices-model-api, in case you wish to deploy it locally.
