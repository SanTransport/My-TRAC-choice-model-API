#!/bin/bash

cp -r ../src .
docker build -t mytrac/choices-model-api:alpha .
docker push mytrac/choices-model-api:alpha 

rm -rf src
