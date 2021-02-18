FROM ubuntu:latest

RUN apt-get update
RUN apt-get install python3 -y
RUN apt-get install python3-pip -y

RUN pip3 install fastapi
RUN pip3 install uvicorn
RUN pip3 install azure-devops
RUN pip3 install jira
RUN pip3 install pyyaml

COPY [".", "."]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]