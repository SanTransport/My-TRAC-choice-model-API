# My-TRAC-choice-model-API

## Breakdown of the various variables of the query string:

**http://<ip_of_the_api>:5000/choice/mode/?**

| Variable name | Value range | example value | Notes |
| --------- | ----------- | ----------- | ----------- |
| user_country | {ES, GR, NL, PT} |  NL | |
| trip_dur_car | {minutes (float)} |  20 | from OTP: trip duration by car (in minutes) |
| trip_dur_pt | {minutes (float)} |  45 | from OTP: trip duration by pt (in minutes) |
| trip_dur_moto | {minutes (float)} |  15 | from OTP: trip duration by moto or bike (in minutes) |
| trip_dur_bike** | {minutes (float)} |  30 | from OTP: trip duration by moto or bike (in minutes) |
| trip_comfort_car | {0, 1} |  1 | |
| trip_comfort_pt | {0, 1} |  0 | |
| trip_comfort_moto | {0, 1} |  1 | |
| trip_comfort_bike** | {0, 1} |  1 | |
| trip_cost_car | {cost in euros (float)} |  5 | cost of using car, as a function of distance |
| trip_cost_moto | {cost in euros (float)} |  2 | cost of using motorbike, as a function of distance |
| trip_cost_bike** | {cost in euros (float)} |  0 | cost of using bike, always equal to 0 |
| trip_cost_pt | {cost of using pt, ticket cost} |  1.5 | |
| trip_purpose | {0, 1} |  0 | * user_traveller_type | 
| user_birthday | {YYYYMMDD}|  19861224 | |
| user_gender | {0, 1} |  1 | |
| user_occupation | {1,2,3,4,5,6} |  3 | |
| user_trips_car | {1,2,3,4} |  4 | * user_often_car | 
| user_trips_pt | {1,2,3,4} |  2 | * user_often_pt | 
| user_car_avail | {0, 1} |  1 | |
| user_bike_avail | {0, 1} |  1 | |
| user_moto_avail | {0, 1} |  1 | |
| trip_id | {string}  |  567 | |
| mytrac_id | {long} |  765 | |

** for the NL model, use the _bike variables instead of the _moto variables.

\* variables that appear with a different name at https://github.com/My-TRAC/data-model

The model may be queried at http://35.190.118.92/choice/help/

The docker can be found here: https://hub.docker.com/r/mytrac/choices-model-api, in case you wish to deploy it locally.
