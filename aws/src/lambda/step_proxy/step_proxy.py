import boto3
import os

def lambda_handler(event, context):
    # Get the SQS message from the event
    message = event['Records'][0]['body']
    
    # Get the state machine ARN from environment variables
    state_machine_arn = os.environ['STATE_MACHINE_ARN']
    
    # Start the Step Functions workflow
    step_functions = boto3.client('stepfunctions')
    try:
        response = step_functions.start_execution(
            stateMachineArn=state_machine_arn,
            input=message
        )
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': 'Error starting Step Functions workflow'
        }

    print(response)

    return {
        'statusCode': 200,
        'body': 'Step Functions workflow started'
    }