FROM ubuntu:latest

RUN apt-get update
RUN apt-get install python3 -y
RUN apt-get install python3-pip -y

RUN pip3 install fastapi
RUN pip3 install uvicorn
RUN pip3 install azure-devops

COPY [".", "."]

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]