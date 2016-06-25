from __future__ import print_function

import json
import urllib
import boto3

print('Loading function')

s3 = boto3.client('s3')
iam = boto3.client('iam')
lambda_client = boto3.client('lambda')


def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    if bucket != "":
        print("This is not the bucket for auto deployment")
        return
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key']).decode('utf8')
    if 'versionId' in event['Records'][0]['s3']['object']:
        version = event['Records'][0]['s3']['object']['versionId'];
    else:
        version = None
    function_values = key.split(".")
    function_name = function_values[0]
    function_type = function_values[1]
    if not (function_type == "zip" or function_type == "config"):
        print("This upload was not in standards. Not handled by this function")
        return
    print("Function name is: %s" % function_name)
    if function_type == "config":
        response = s3.get_object(Bucket=bucket, Key=key)
        config_str = response['Body'].read()
        config = json.loads(config_str)
        arn = iam.get_role(RoleName=config['Role'])['Role']['Arn']
        config['Role'] = arn
    try:
        resp = lambda_client.get_function(FunctionName=function_name)
        exist = True
    except Exception as e:
        print(e)
        exist = False
    if exist:
        print("Need to update")
        if function_type == "zip":
            args = {
                'FunctionName': function_name,
                'S3Bucket': bucket,
                'S3Key': key,
                'Publish': True
            }
            if version:
                args['S3ObjectVersion'] = version
            response = lambda_client.update_function_code(**args)
        elif function_type == "config":
            config.pop('Runtime')
            config.pop('Publish')
            response = lambda_client.update_function_configuration(**config)
        print(response)
        return
    else:
        print("Need to create")
        if function_type == "config":
            config['Code'] = {'S3Bucket': bucket, 'S3Key': function_name + ".zip"}
            if version:
                config['Code']['S3ObjectVersion'] = version
            response = lambda_client.create_function(**config)
            print(response)
        return
