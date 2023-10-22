# prepopulate_start


--signature-type cloudevent

functions-framework --target=precalc_model

# Queue
Populate the queue with the list of the client models-utm types pairs.

The code is deployed as a cloud funciton precalc-models
https://console.cloud.google.com/functions/details/us-east1/precalc-models?env=gen2&project=pcg-mta

In order to update, just overwrite the script file of precalc-models Cloud Function.
Note, that if re-deplying the function under a different name, an SQL connection needs to be added in the function configuration section. 
Same is applicable if a new SQL database is configured.
To access the configuration, navigate to the function name, click Edit Function, open Runtime, build, connection and security settings, select Connections tab and select the relevant connection.