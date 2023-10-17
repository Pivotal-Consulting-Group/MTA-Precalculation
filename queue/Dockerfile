FROM python:3.10-bullseye

RUN mkdir -p /app/  
COPY requirements.txt /app/requirements.txt

RUN set -ex \
    #&& python -m venv /env \
    && pip3 install --upgrade pip \
    && pip3 install gunicorn \
    && pip3  install --no-cache-dir -r /app/requirements.txt 

COPY . /app/
COPY ./dot_env /app/.env
WORKDIR /app


#ARG buildtime_variable1=default_value 
#ENV AWS_ACCESS_KEY_ID=$buildtime_variable1
#ARG buildtime_variable2=default_value 
#ENV AWS_SECRET_ACCESS_KEY=$buildtime_variable2
#ENV VIRTUAL_ENV /env
#ENV PATH /env/bin:$PATH

EXPOSE 80

CMD ["gunicorn", "--bind", ":80", "--workers", "3", "coreapi.wsgi"]
# CMD ["python3", "manage.py","process_queue"]
# CMD ["python3", "manage.py", "runserver", "0.0.0.0:80"]