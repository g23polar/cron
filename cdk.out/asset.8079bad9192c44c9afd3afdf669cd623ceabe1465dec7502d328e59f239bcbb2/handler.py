"""
Example cron job handler.

This runs as an AWS Lambda function triggered by EventBridge on a schedule.
"""

import json


def main(event, context):
    """
    Lambda handler function.

    Args:
        event: EventBridge scheduled event payload
        context: Lambda context object

    Returns:
        dict: Response with status
    """
    print(f"Event received: {json.dumps(event)}")
    print("Example job running...")

    # Your job logic goes here
    # - Web scraping
    # - LLM API calls
    # - Data processing
    # - etc.

    result = {"status": "success", "message": "Example job completed"}
    print(f"Result: {json.dumps(result)}")

    return result
