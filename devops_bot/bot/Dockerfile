FROM python:3.10
RUN apt-get update && apt-get install -y ssh
WORKDIR /bot
COPY requirements.txt requirements.txt
#RUN apt install python3-pip
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "main.py"]
