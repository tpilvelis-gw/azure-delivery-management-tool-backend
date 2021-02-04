docker build -t azure-delivery-management-api .
docker run -d --name mycontainer -p 80:80 azure-delivery-management-api