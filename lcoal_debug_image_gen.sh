#!/bin/bash
# Deploy pods to kubernetes cluster 
skaffold run


# Port forward all services
kubectl port-forward svc/productcatalogservice 3550:3550 &
kubectl port-forward svc/currencyservice 7000:7000 &
kubectl port-forward svc/cartservice 7070:7070 &
kubectl port-forward svc/recommendationservice 8081:8081 &
kubectl port-forward svc/checkoutservice 5050:5050 &
kubectl port-forward svc/shippingservice 50051:50051 &
kubectl port-forward svc/adservice 9555:9555 &
kubectl port-forward svc/shoppingassistantservice 9000:9000 


# Run frontend
go run src/frontend/main.go
# Run image generation service locally
python3 src/imagegenerationservice/imagegenservice.py