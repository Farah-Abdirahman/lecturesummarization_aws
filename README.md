
# Audio Transcription & Summarization Pipeline with Amazon Bedrock

This project demonstrates an event-driven architecture for automatically transcribing audio files and generating summaries using AWS services, including Amazon Bedrock's foundation models. The application provides a streamlined workflow for processing audio content and extracting valuable insights.

## Demo Video

[![Watch the demo video](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)

*Replace YOUR_VIDEO_ID with your actual YouTube video ID*

## Architecture

![Architecture Diagram](architecture_diagram.png)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │     │             │
│  Audio File ├────►│  S3 Bucket  ├────►│  Lambda 1   ├────►│  Transcribe │
│             │     │  (Audio)    │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                   │
                                                                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│             │     │             │     │             │     │             │
│  Streamlit  │◄────┤  S3 Bucket  │◄────┤  Lambda 2   │◄────┤  Transcript │
│     UI      │     │   (Text)    │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                          ▲                                        │
                          │                                        │
                          │           ┌─────────────┐              │
                          │           │             │              │
                          └───────────┤   Bedrock   │◄─────────────┘
                                      │             │
                                      └─────────────┘
```

### Event-Driven Workflow

1. **Audio Upload**:
   - User uploads an audio file through the Streamlit UI
   - File is stored in the audio S3 bucket
   - **S3 event notification** automatically triggers the first Lambda function

2. **Transcription Trigger**:
   - **Lambda function 1** (`lambda_transcribe.py`) is triggered by the S3 upload event
   - Lambda function starts an Amazon Transcribe job with speaker diarization
   - No manual intervention is needed - the process is fully automated

3. **Transcription Process**:
   - Amazon Transcribe processes the audio file
   - Transcript is saved to the text S3 bucket
   - **S3 event notification** automatically triggers the second Lambda function

4. **Summarization Trigger**:
   - **Lambda function 2** (`lambda_summarize.py`) is triggered by the S3 event when a new transcript is created
   - Lambda function calls Amazon Bedrock to generate a summary
   - This happens automatically without any manual steps

5. **Summary Generation**:
   - Amazon Bedrock processes the transcript using the configured foundation model
   - Generated summary is saved back to the text S3 bucket

6. **User Interface**:
   - Streamlit application displays the transcript and summary
   - Application can also generate summaries on-demand if needed
   - The UI polls for the results of the automated processing

## Features

- Upload audio files (MP3, WAV)
- Transcribe audio using AWS Transcribe with speaker diarization
- Automatically summarize transcripts using Amazon Bedrock foundation models
- Display transcriptions with speaker labels
- Analyze conversations for key topics and sentiment
- View demo transcripts and summaries
- Event-driven architecture for scalable processing

## AWS Services Used

- **Amazon S3**: Storage for audio files, transcripts, and summaries
- **AWS Lambda**: Serverless functions for event-driven processing
- **Amazon Transcribe**: Speech-to-text service with speaker diarization
- **Amazon Bedrock**: Foundation model service for text summarization
- **Amazon EventBridge**: Event bus for coordinating the workflow (implicit in S3 event notifications)
- **Amazon CloudWatch**: Monitoring and logging for the application components

## Setup Instructions

### Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured with credentials
- Python 3.8 or higher
- Streamlit

### Deployment

1. Clone this repository:
   ```
   git clone <repository-url>
   cd LLM-Apps-With-Amazon-Bedrock
   ```

2. Install the required dependencies:
   ```
   pip install -r streamlit_requirements.txt
   ```

3. Deploy the CloudFormation stack:
   ```
   aws cloudformation deploy --template-file template.yaml --stack-name bedrock-audio-pipeline --capabilities CAPABILITY_IAM
   ```

4. Set up environment variables using the setup script:
   ```
   # For Linux/macOS
   chmod +x setup.sh
   ./setup.sh
   
   # For Windows
   run_demo.bat
   ```

5. Run the Streamlit app:
   ```
   streamlit run src/app.py
   ```

## Environment Variables

The application uses the following environment variables:
- `LEARNER_S3_BUCKETNAME_TEXT`: S3 bucket for storing transcripts (default: 'summary-llm')
- `LEARNER_S3_BUCKETNAME_AUDIO`: S3 bucket for storing audio files (default: 'audiotranscribe-bucket')
- `BEDROCK_MODEL_ID`: Amazon Bedrock model ID (default: 'amazon.nova-lite-v1:0')

## Demo

The app includes a demo feature that loads a pre-existing transcript and summary of a conversation. This allows you to explore the functionality without uploading your own audio files.

## Project Structure

```
LLM Apps With Amazon Bedrock/
├── helpers/
│   ├── CloudWatchHelper.py
│   ├── Display_Helper.py
│   ├── Lambda_Helper.py
│   └── S3_Helper.py
├── src/
│   ├── app.py              # Streamlit application
│   └── lambda_summarize.py # Lambda function for summarization
├── architecture.md         # Detailed architecture documentation
├── demo-summary.txt        # Sample summary for demo
├── demo-transcript.json    # Sample transcript for demo
├── prompt_template.txt     # Prompt template for Bedrock
├── README.md               # This file
├── run_demo.bat            # Windows setup script
├── run_demo.sh             # Linux/macOS setup script
├── setup.sh                # Environment setup script
└── streamlit_requirements.txt # Python dependencies
