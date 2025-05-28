import streamlit as st
import boto3
import json
import os
import re
import uuid
import time
from helpers.S3_Helper import S3_Helper

# Initialize S3 helper
s3_helper = S3_Helper()

# Set environment variables if not already set
if 'LEARNER_S3_BUCKETNAME_TEXT' not in os.environ:
    os.environ['LEARNER_S3_BUCKETNAME_TEXT'] = 'summary-llm'
if 'LEARNER_S3_BUCKETNAME_AUDIO' not in os.environ:
    os.environ['LEARNER_S3_BUCKETNAME_AUDIO'] = 'audiotranscribe-bucket'


# Get bucket names from environment variables
bucket_name_text = os.environ['LEARNER_S3_BUCKETNAME_TEXT']
bucket_name_audio = os.environ['LEARNER_S3_BUCKETNAME_AUDIO']

# Initialize AWS clients. I used 'us-east-1' as a common regio
transcribe_client = boto3.client('transcribe', region_name='us-east-1')
s3_client = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

def upload_to_s3(file_bytes, filename):
    """Upload a file to S3 bucket"""
    try:
        # Save the file locally first
        with open(filename, "wb") as f:
            f.write(file_bytes)
        
        # Upload to S3
        s3_helper.upload_file(bucket_name_audio, filename)
        return True
    except Exception as e:
        st.error(f"Error uploading to S3: {e}")
        return False

def start_transcription_job(filename):
    """Start an AWS Transcribe job"""
    try:
        job_name = 'transcription-job-' + str(uuid.uuid4())
        
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': f's3://{bucket_name_audio}/{filename}'},
            MediaFormat=filename.split('.')[-1],
            LanguageCode='en-US',
            OutputBucketName=bucket_name_text,
            OutputKey=f'{job_name}.json',
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 2
            }
        )
        return job_name
    except Exception as e:
        st.error(f"Error starting transcription job: {e}")
        return None

def check_job_status(job_name):
    """Check the status of a transcription job"""
    try:
        response = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        return response['TranscriptionJob']['TranscriptionJobStatus']
    except Exception as e:
        st.error(f"Error checking job status: {e}")
        return "ERROR"

def get_transcript(job_name):
    """Get the transcript from S3 after job completion"""
    try:
        # Download the transcript file
        transcript_key = f"{job_name}.json"
        local_path = f"./{transcript_key}"
        
        s3_client.download_file(bucket_name_text, transcript_key, local_path)
        
        # Read and parse the transcript
        with open(local_path, 'r') as file:
            transcript_data = json.load(file)
        
        return transcript_data
    except Exception as e:
        st.error(f"Error getting transcript: {e}")
        return None

def format_transcript_for_display(transcript_data):
    """Format the transcript data for display"""
    if not transcript_data or 'results' not in transcript_data:
        return "No transcript data available."
    
    formatted_text = ""
    
    # Extract speaker segments
    if 'speaker_labels' in transcript_data['results']:
        segments = transcript_data['results']['speaker_labels']['segments']
        items = transcript_data['results']['items']
        
        # Create a mapping of start_time to item
        time_to_item = {}
        for item in items:
            if 'start_time' in item:
                time_to_item[item['start_time']] = item
        
        # Process each segment by speaker
        current_speaker = ""
        current_text = ""
        
        for segment in segments:
            speaker = segment['speaker_label']
            
            if speaker != current_speaker and current_text:
                formatted_text += f"{current_speaker}: {current_text}\n"
                current_text = ""
            
            current_speaker = speaker
            
            for item in segment['items']:
                if 'start_time' in item and item['start_time'] in time_to_item:
                    word_item = time_to_item[item['start_time']]
                    if 'alternatives' in word_item and word_item['alternatives']:
                        word = word_item['alternatives'][0]['content']
                        current_text += word + " "
        
        # Add the last speaker's text
        if current_text:
            formatted_text += f"{current_speaker}: {current_text}\n"
    else:
        # Fallback to simple transcript
        formatted_text = transcript_data['results']['transcripts'][0]['transcript']
    
    return formatted_text

client = boto3.client("bedrock-runtime", region_name="us-east-1")
LITE_MODEL_ID = "amazon.nova-lite-v1:0"



def generate_summary(transcript_text):
    """Generate a summary using Amazon Bedrock"""
    system_prompt = [
    {
        "text": f"""Summarize the following conversation transcript. 
Focus on the main topics discussed, key points, and any decisions or actions agreed upon.
Keep the summary concise but comprehensive.

Transcript:
{transcript_text}

Summary:"""
    }
]
    inf_params = {"maxTokens": 1000, "topP": 0.9, "topK": 20, "temperature": 0.3}
    message_list = [{"role": "user", "content": [{"text": transcript_text}]}]

    try:
        request_body = {
        "schemaVersion": "messages-v1",
        "system": system_prompt,
        "messages": message_list,
        "inferenceConfig": inf_params
        }
        

        response = client.invoke_model(
            modelId=LITE_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        result = json.loads(response["body"].read())
         # Print the structure to debug
        print("Response structure:", json.dumps(result, indent=2)[:200] + "...")
        
        if "message" in result and "content" in result["message"]:
            content = result["message"]["content"]
            if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
                return content[0]["text"]
        elif "output" in result and "message" in result["output"]:
            if "content" in result["output"]["message"]:
                content = result["output"]["message"]["content"]
                if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
                    return content[0]["text"]
        
        result_str = str(result)
        match = re.search(r"'text': '(.*?)(?:'|\")", result_str, re.DOTALL)
        if match:
            return match.group(1)
        
        return str(result)
            
    except Exception as e:
        st.error(f"Error during model invocation: {str(e)}")
        return f"Error: {str(e)}"

def check_for_summary(job_name):
    """Check if a summary exists for the given job"""
    summary_key = f"{job_name}-summary.txt"
    try:
        s3_client.head_object(Bucket=bucket_name_text, Key=summary_key)
        return True
    except:
        return False

def get_summary(job_name):
    """Get the summary from S3"""
    summary_key = f"{job_name}-summary.txt"
    local_path = f"./{summary_key}"
    
    try:
        s3_client.download_file(bucket_name_text, summary_key, local_path)
        
        with open(local_path, 'r') as file:
            summary = file.read()
        
        return summary
    except Exception as e:
        st.error(f"Error getting summary: {e}")
        return None

def analyze_conversation(transcript_text):
    """Analyze the conversation for key points"""
    analysis = {
        "speakers": set(),
        "topics": [],
        "sentiment": "Neutral"
    }
    
    lines = transcript_text.split('\n')
    
    # Extract speakers
    for line in lines:
        if ': ' in line:
            speaker = line.split(': ')[0]
            analysis["speakers"].add(speaker)
    
    # Simple topic detection
    if "wedding anniversary" in transcript_text.lower():
        analysis["topics"].append("Anniversary Celebration")
    
    if "diamond suite" in transcript_text.lower():
        analysis["topics"].append("Luxury Accommodation")
    
    if "moonlit pool" in transcript_text.lower() or "star deck" in transcript_text.lower():
        analysis["topics"].append("Special Amenities")
    
    if "pre authorization" in transcript_text.lower() or "$1000" in transcript_text:
        analysis["topics"].append("Payment and Charges")
    
    # Simple sentiment analysis
    positive_words = ["fantastic", "heavenly", "exceptional", "special", "worth"]
    negative_words = ["excessive", "concern"]
    
    positive_count = sum(1 for word in positive_words if word in transcript_text.lower())
    negative_count = sum(1 for word in negative_words if word in transcript_text.lower())
    
    if positive_count > negative_count:
        analysis["sentiment"] = "Positive"
    elif negative_count > positive_count:
        analysis["sentiment"] = "Negative"
    
    return analysis

# Streamlit UI
st.title("Audio Transcription & Summarization Pipeline")
st.write("This app demonstrates an event-driven architecture for audio transcription and summarization using AWS services including Amazon Bedrock.")

# File upload
uploaded_file = st.file_uploader("Upload an audio file (MP3, WAV)", type=["mp3", "wav"])

if uploaded_file:
    st.audio(uploaded_file, format=f'audio/{uploaded_file.name.split(".")[-1]}')
    
    if st.button("Process Audio"):
        with st.spinner("Uploading file to S3..."):
            # Upload the file to S3
            success = upload_to_s3(uploaded_file.getvalue(), uploaded_file.name)
            
            if success:
                st.success(f"File uploaded to S3 bucket: {bucket_name_audio}")
                
                # Start transcription job
                with st.spinner("Starting transcription job..."):
                    job_name = start_transcription_job(uploaded_file.name)
                    
                    if job_name:
                        st.success(f"Transcription job started: {job_name}")
                        
                        # Poll for job completion
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status = "IN_PROGRESS"
                        while status == "IN_PROGRESS":
                            status = check_job_status(job_name)
                            status_text.text(f"Job status: {status}")
                            progress_bar.progress(50 if status == "IN_PROGRESS" else 100)
                            if status == "IN_PROGRESS":
                                time.sleep(5)
                        
                        if status == "COMPLETED":
                            st.success("Transcription completed!")
                            
                            # Get and display transcript
                            transcript_data = get_transcript(job_name)
                            if transcript_data:
                                formatted_transcript = format_transcript_for_display(transcript_data)
                                
                                st.subheader("Transcript")
                                st.text_area("Full Transcript", formatted_transcript, height=300)
                                
                                # Check if summary exists (from event-driven Lambda)
                                summary_exists = check_for_summary(job_name)
                                
                                if summary_exists:
                                    # Get the summary generated by the Lambda function
                                    summary = get_summary(job_name)
                                    if summary:
                                        st.subheader("Summary (Generated by Lambda)")
                                        st.text_area("Summary", summary, height=200)
                                else:
                                    # Generate summary on-demand
                                    st.info("No automated summary found. Generating summary now...")
                                    summary = generate_summary(formatted_transcript)
                                    
                                    st.subheader("Summary (Generated On-Demand)")
                                    st.text_area("Summary", summary, height=200)
                                
                                # Analyze the conversation
                                analysis = analyze_conversation(formatted_transcript)
                                
                                st.subheader("Conversation Analysis")
                                st.write(f"**Speakers:** {', '.join(analysis['speakers'])}")
                                st.write(f"**Topics Discussed:**")
                                for topic in analysis["topics"]:
                                    st.write(f"- {topic}")
                                st.write(f"**Overall Sentiment:** {analysis['sentiment']}")
                        else:
                            st.error(f"Transcription failed with status: {status}")

# Demo with pre-existing transcript
st.markdown("---")
st.subheader("Or view a demo transcript and summary")

if st.button("Load Demo"):
    # Load the demo transcript
    try:
        with open("transcript.txt", "r") as f:
            demo_transcript = f.read()
        
        # Load or generate demo summary
        try:
            with open("demo-summary.txt", "r") as f:
                demo_summary = f.read()
        except:
            demo_summary = """
This conversation is between a customer (Alex) and a hotel representative at Crystal Heights Hotel in Singapore. The customer is looking to book a room for his 10th wedding anniversary. Key points:

1. The hotel offers various room types with views of the city skyline and Sapphire Bay.
2. The customer books a Diamond Suite which includes access to the moonlit pool and star deck.
3. The package includes breakfast, spa treatment for two, and a romantic dinner.
4. The booking is for October 10th to 17th.
5. There is a $1000 pre-authorization hold required, which the customer initially finds excessive.
6. Additional charges include a 10% service charge and 7% fantasy tax.
7. Despite concerns about the charges, the customer proceeds with the booking as it's for a special occasion.

The conversation ends positively with the hotel representative assuring the customer that their experience will be worth it.
"""
            # Save for future use
            with open("demo-summary.txt", "w") as f:
                f.write(demo_summary)
        
        st.subheader("Demo Transcript")
        st.text_area("Full Transcript", demo_transcript, height=300)
        
        st.subheader("Summary")
        st.text_area("Summary", demo_summary, height=200)
        
        # Analyze the conversation
        analysis = analyze_conversation(demo_transcript)
        
        st.subheader("Conversation Analysis")
        st.write(f"**Speakers:** {', '.join(analysis['speakers'])}")
        st.write(f"**Topics Discussed:**")
        for topic in analysis["topics"]:
            st.write(f"- {topic}")
        st.write(f"**Overall Sentiment:** {analysis['sentiment']}")
    except Exception as e:
        st.error(f"Error loading demo: {e}")