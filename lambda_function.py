import boto3
import json
from jinja2 import Template

s3_client = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime','us-west-2')

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    if '-transcription.json' not in key:
        print("This demo only works with *-transcript.json.")
        return
    try:

        file_content = ""

        response = s3_client.get_object(Bucket=bucket,Key=key)

        file_content = response['Body'].read().decode('utf-8')
        transcript = extract_transcript_from_textract(file_content)
        print(f'Successfully read file {key} from Bucket {bucket}')
        print(f'Transcript is {transcript}')

        summary = bedrock_summarization(transcript)

        s3_client.put_object(
            Bucket = bucket,
            Key= 'result.txt',
            Body = summary,
            ContentType = 'text/plain'

        )
        

    




    except Exception as e:

        print(f"Error occurred: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error occurred: {e}")
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps(f"Successfully summarized {key} from bucket {bucket}. Summary: {summary}")
    }







def bedrock_summarization(transcript):
    with open('prompt_template.txt','r') as file:
        template_string = file.read()

    data = {
        'transcript': transcript,
        'topics':['charges', 'location', 'availability']
    }

    template = Template(template_string)
    prompt = template.render(data)

    kwargs = {
        "modelId": "amazon.titan-text-express-v1",
        "contentType": "application/json",
        "accept": "*/*",
        "body": json.dumps(
            {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 2048,
                    "stopSequences": [],
                    "temperature": 0, #We want the model to be more consistent
                    "topP": 0.9
                }
            }
        )
    }
    
    response = bedrock_runtime.invoke_model(**kwargs)

    summary = json.loads(response.get('body').read()).get('results')[0].get('outputText')    
    return summary

def extract_transcript_from_textract(file_content):

    transcript_json = json.loads(file_content)

    output_text = ""
    current_speaker = None

    items = transcript_json['results']['items']

    # Iterate through the content word by word:
    for item in items:
        speaker_label = item.get('speaker_label', None)
        content = item['alternatives'][0]['content']
        
        # Start the line with the speaker label:
        if speaker_label is not None and speaker_label != current_speaker:
            current_speaker = speaker_label
            output_text += f"\n{current_speaker}: "
        
        # Add the speech content:
        if item['type'] == 'punctuation':
            output_text = output_text.rstrip()  # Remove the last space
        
        output_text += f"{content} "
        
    return output_text
        
