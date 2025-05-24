# LLMs with Amazon Bedrock: Audio Transcription & Summarization

This project provides an event-driven pipeline to **transcribe audio from lectures or lessons and summarize the content automatically using Amazon Bedrock**. The workflow leverages AWS Lambda, Amazon S3, Amazon Transcribe, and Bedrock's Titan LLM to deliver concise summaries from raw audio files.

## Features

- **Automated transcription:** Upload an audio file (e.g., MP3) to S3 and trigger a transcription job.
- **Summarization with LLM:** Extracts the transcript, applies a prompt-template, and generates a summary using Amazon Bedrock (Titan model).
- **Event-driven AWS architecture:** Uses Lambda functions for orchestration and automation.
- **Customizable prompt templates:** Easily adapt summary requirements via Jinja2 templates.

## Architecture Overview

1. **Audio Upload:** Place a lecture or lesson audio file (e.g., `dialog.mp3`) in a designated S3 bucket.
2. **Transcription:** An AWS Lambda function is triggered, launching an Amazon Transcribe job to create a transcript file (`*-transcript.json`).
3. **Summarization:** When the transcript is ready, another Lambda function:
    - Extracts the transcript.
    - Renders a prompt using `prompt_template.txt`.
    - Calls Amazon Bedrock (Titan) to summarize the content.
    - Stores the summary (e.g., `result.txt`) back to S3.
4. **Outputs:** JSON summary containing sentiment, main issues/topics, and an overall overview.

## Example Prompt Template

The summarization prompt (from `prompt_template.txt`) expects the LLM to generate structured JSON including sentiment and actionable issues. You can customize this template as needed.

## AWS Setup

- **Python 3.10** recommended.
- AWS Services required:
  - S3
  - Lambda
  - Amazon Transcribe
  - Amazon Bedrock (Titan model)
- **IAM permissions** for Lambda to access S3, Transcribe, and Bedrock.

### Quickstart

1. **Clone the repo and install requirements:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Configure AWS credentials:**
    - Create an AWS account and IAM user with sufficient privileges.
    - Install and configure AWS CLI:
      ```
      aws configure
      ```
    - (See comments in `requirements.txt` for setup links.)

3. **Deploy the Lambda function:**
    - Use the provided `setup.sh` script to export CloudFormation stack outputs as environment variables.
    - Deploy Lambda functions (see notebooks for deployment helpers).

4. **Run the pipeline:**
    - Upload an audio file to the S3 audio bucket.
    - The pipeline will transcribe and summarize automatically.
    - Retrieve results from the designated S3 bucket.

## File Structure

- `lambda_function.py` - Main Lambda logic for transcript extraction and summarization.
- `prompt_template.txt` - Jinja2 template for summary prompt.
- `setup.sh` - Script to set AWS environment variables from CloudFormation.
- `requirements.txt` - Python dependencies.
- `event_driven.ipynb`, `first_generation.ipynb`, `lambdafunc.ipynb`, `logging.ipynb`, `summarize_audio.ipynb` - Example and helper notebooks.
- `helpers/` - Utility modules (e.g., for logging/CloudWatch).

## Example Workflow (Pseudocode)

```python
# 1. Lambda triggered by new transcription JSON in S3
def lambda_handler(event, context):
    # ...
    transcript = extract_transcript_from_textract(file_content)
    summary = bedrock_summarization(transcript)
    s3_client.put_object(Bucket=bucket, Key='result.txt', Body=summary)
```

## Customization

- **Prompt template:** Edit `prompt_template.txt` to change summary format or requirements.
- **Topics:** Adjust topics in `lambda_function.py` for domain-specific summaries.

## License

[MIT License](LICENSE) (or specify your license here)

---

**Note:** For full context and all files, see the repository on GitHub: [llmswithamazonbedrock](https://github.com/Farah-Abdirahman/llmswithamazonbedrock/).
