#/bin/bash

echo "Deployin Mode Choice models..."

kubectl apply -f mysql-deployment.yaml 
sleep 60

kubectl apply -f model-deployment.yaml

