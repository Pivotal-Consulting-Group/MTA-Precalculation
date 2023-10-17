import psycopg2 
import base64
import functions_framework
import os
import json
import typing
import hashlib
from google.cloud import secretmanager,pubsub_v1
from concurrent import futures
import sqlalchemy


PROJECT_ID = "pcg-mta"
TOPIC_ID = "precalc-models"
    
def connect_unix_socket(passp):
    """Initializes a Unix socket connection pool for a Cloud SQL instance of Postgres."""
    # Note: Saving credentials in environment variables is convenient, but not
    # secure - consider a more secure solution such as
    # Cloud Secret Manager (https://cloud.google.com/secret-manager) to help
    # keep secrets safe.
    db_user = 'postgres'
    db_pass = passp
    db_name = 'mta_test'
    unix_socket_path = '/cloudsql/pcg-mta:us-east1:mta-test'

    pool = sqlalchemy.create_engine(
        # Equivalent URL:
        # postgresql+pg8000://<db_user>:<db_pass>@/<db_name>
        #                         ?unix_sock=<INSTANCE_UNIX_SOCKET>/.s.PGSQL.5432
        # Note: Some drivers require the `unix_sock` query parameter to use a different key.
        # For example, 'psycopg2' uses the path set to `host` in order to connect successfully.
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={"unix_sock": f"{unix_socket_path}/.s.PGSQL.5432"},
        ),
        # ...
    )
    return pool

def send_message(msg): 
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
    # Data must be a bytestring
    msg = json.dumps(msg, default=str).encode("utf-8")
    
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
    print("topic_path----------------------",topic_path)
    publish_futures = []
    def get_callback(
        publish_future: pubsub_v1.publisher.futures.Future, data: str
    ) -> typing.Callable[[pubsub_v1.publisher.futures.Future], None]:
        def callback(publish_future: pubsub_v1.publisher.futures.Future) -> None:
            try:
                # Wait 60 seconds for the publish call to succeed.
                print(publish_future.result(timeout=60))
            except futures.TimeoutError:
                print(f"Publishing {data} timed out.")

        return callback


    # When you publish a message, the client returns a future.
    publish_future = publisher.publish(topic_path, msg)
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(get_callback(publish_future, msg))
    publish_futures.append(publish_future)

    # Wait for all the publish futures to resolve before exiting.
    #futures.wait(publish_futures, return_when=futures.ALL_COMPLETED)

    print(f"Published messages with error handler to {topic_path}.")    


def get_secret( secret_name = "django-settings",version_id="latest"):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()
    # Build the resource name of the secret version.
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/{version_id}"
    #print(" obtaining secret =====================", name)
    # Access the secret version.
    response = client.access_secret_version(name=name)
    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')


def secret_to_dict(s):
    res = {}
    ss = s.split("\n")
    for s0 in ss:
        s_key = s0.split("=")[0]
        s_value = s0.split("=")[-1]
        res[s_key] = s_value
    return res


@functions_framework.http
def precalc_model(request):
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json and 'name' in request_json:
        name = request_json['name']
    elif request_args and 'name' in request_args:
        name = request_args['name']
    else:
        name = 'World'
    print(name)
    
    #forming the connection
    DATABASE_PASS = get_secret( "test-db")
    
    conn = psycopg2.connect(database="mta_test", user = "postgres", password = DATABASE_PASS, host = '/cloudsql/pcg-mta:us-east1:mta-test')
    print(conn)
    #conn = psycopg2.connect(database="postgres", user='postgres', password=DATABASE_PASS, host='/cloudsql/pcg-mta:us-east1:mta-test', port='5432'  )

    # Creating a cursor object with cursor() method
    cursor = conn.cursor()
    # Fetching Data From articals Table
    sql = """SELECT id FROM public."MTAapp_client" where status='Active'"""
    #sql = """select * from information_schema.tables"""
    cursor.execute(sql)
    clients = cursor.fetchall()
    print(clients)
    config_str = get_secret()
    config = secret_to_dict(config_str)
    
    utm_types = config["utm_types"]
    model_types = config["model_types"]
    utm_types = utm_types[1:-1]
    utm_types = utm_types.split(",")
    print(utm_types)
    cursor = conn.cursor()

    res_msgs = []    
    for client in clients:
        client_id = client[0]
        sql_table = f"""SELECT distinct(table_name) FROM public."MTAapp_crmfieldconfig" where client_id = {client_id} limit 1"""
        cursor1 = conn.cursor()
        cursor1.execute(sql_table)
        table_name = cursor1.fetchall()[0][0]
        print("table_name",table_name)
        
        sql_outcome = f"""select distinct(field_name) FROM public."MTAapp_crmfieldconfig" where client_id = {client_id} and table_name='{table_name}' and pcg_name='date' limit 1"""
        print(sql_outcome)
        cursor2 = conn.cursor()
        cursor2.execute(sql_outcome)
        default_outcome_type = cursor2.fetchall()[0][0]
        print("default_outcome_type",default_outcome_type)
        
        for utm_type in utm_types:
            for model_type in model_types:
                msg = {"client_id":client_id, "model_type":model_type,"utm_type": utm_type, "table_name":table_name,"replace_outcome_type": default_outcome_type}
                send_message(msg)
                res_msgs.append(str(msg))
    return '\n'.join(res_msgs)        
    
