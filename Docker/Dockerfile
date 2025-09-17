# importing base image
FROM python:3.9

# creating working dir
WORKDIR /app

# copying files
COPY . /app

# install dependancy
RUN pip install -r requirements.txt

# run the application
CMD ["python","app.py"]

