# pragma: no cover
import os
import logging
import boto3
from functools import wraps
import traceback

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize X-Ray if available
try:
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.core import patch_all

    # Check if running in Lambda/production environment
    if os.environ.get("AWS_EXECUTION_ENV") is not None:
        logger.info("Initializing AWS X-Ray")
        # Configure sampling rules if needed
        xray_recorder.configure(sampling=True, context_missing="LOG_ERROR")
        # Patch all supported libraries
        patch_all()
        XRAY_AVAILABLE = True
    else:
        logger.info("Not running in AWS environment, X-Ray disabled")
        XRAY_AVAILABLE = False
except ImportError:
    logger.info("AWS X-Ray SDK not installed, X-Ray features will be disabled")
    XRAY_AVAILABLE = False


def trace_function(name=None):
    """
    Decorator for tracing functions with X-Ray if available

    Args:
        name (str, optional): Custom name for the subsegment

    Returns:
        function: Decorated function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not XRAY_AVAILABLE:
                return func(*args, **kwargs)

            segment_name = name or func.__name__

            try:
                # Begin subsegment
                subsegment = xray_recorder.begin_subsegment(segment_name)

                # Add metadata about function parameters
                if subsegment:
                    # Only include non-sensitive arguments
                    safe_args = []
                    for arg in args:
                        if isinstance(arg, (str, int, float, bool, list, dict)):
                            # For large objects, just log the type and size
                            if isinstance(arg, (dict, list)) and len(str(arg)) > 1000:
                                safe_args.append(f"{type(arg).__name__} of size {len(str(arg))}")
                            else:
                                safe_args.append(arg)
                        else:
                            safe_args.append(f"<{type(arg).__name__}>")

                    safe_kwargs = {}
                    for key, value in kwargs.items():
                        # Skip adding sensitive keywords
                        if key.lower() in ["password", "token", "secret", "key", "authorization"]:
                            safe_kwargs[key] = "<redacted>"
                        elif isinstance(value, (str, int, float, bool, list, dict)):
                            # For large objects, just log the type and size
                            if isinstance(value, (dict, list)) and len(str(value)) > 1000:
                                safe_kwargs[
                                    key
                                ] = f"{type(value).__name__} of size {len(str(value))}"
                            else:
                                safe_kwargs[key] = value
                        else:
                            safe_kwargs[key] = f"<{type(value).__name__}>"

                    subsegment.put_metadata(
                        "parameters", {"args": safe_args, "kwargs": safe_kwargs}, "function"
                    )

                # Call the function
                result = func(*args, **kwargs)

                # Add result metadata if available
                if subsegment:
                    # Only include non-sensitive and reasonably sized results
                    if isinstance(result, (str, int, float, bool)):
                        subsegment.put_metadata("result", result, "function")
                    elif isinstance(result, (dict, list)) and len(str(result)) < 1000:
                        subsegment.put_metadata("result", result, "function")
                    else:
                        subsegment.put_metadata(
                            "result", f"{type(result).__name__} returned", "function"
                        )

                return result
            except Exception as e:
                if XRAY_AVAILABLE and xray_recorder:
                    subsegment = xray_recorder.current_subsegment()
                    if subsegment:
                        subsegment.add_exception(
                            exception=e, stack=traceback.extract_stack(), remote=False
                        )
                raise
            finally:
                # End subsegment if X-Ray is available
                if XRAY_AVAILABLE:
                    xray_recorder.end_subsegment()

        return wrapper

    return decorator


def trace_lambda_handler(name=None):
    """
    Decorator specifically for Lambda handlers to capture additional context

    Args:
        name (str, optional): Custom name for the segment

    Returns:
        function: Decorated Lambda handler
    """

    def decorator(handler):
        @wraps(handler)
        def wrapper(event, context):
            if not XRAY_AVAILABLE:
                return handler(event, context)

            segment_name = name or context.function_name

            # Start a segment/ensure segment exists
            segment = xray_recorder.current_segment()
            if segment:
                try:
                    segment.name = segment_name
                except Exception as e:
                    if "FacadeSegment" in str(e):
                        logger.info(f"Cannot set name on FacadeSegment: {str(e)}")
                    else:
                        logger.warning(f"Failed to set segment name: {str(e)}")

            # Add Lambda context information to the segment - safely handling FacadeSegments
            try:
                segment.put_annotation("function_name", context.function_name)
                segment.put_annotation("function_version", context.function_version)
                segment.put_annotation("memory_limit_mb", context.memory_limit_in_mb)

                # Add cold start annotation
                global_xray_recorder = xray_recorder
                is_cold_start = getattr(global_xray_recorder, "is_cold_start", True)
                segment.put_annotation("cold_start", is_cold_start)
            except Exception as e:
                # Handle FacadeSegmentMutationException gracefully
                if "FacadeSegment" in str(e):
                    logger.info(f"Skipping X-Ray annotations for FacadeSegment: {str(e)}")
                else:
                    logger.warning(f"Failed to add X-Ray annotations: {str(e)}")

            # Mark lambda as no longer cold starting
            if hasattr(global_xray_recorder, "is_cold_start"):
                global_xray_recorder.is_cold_start = False

            # Add event information to metadata (safely)
            try:
                safe_event = scrub_sensitive_data(event)
                segment.put_metadata("event", safe_event, "lambda")
            except Exception as e:
                if "FacadeSegment" in str(e):
                    logger.info(f"Skipping X-Ray metadata for FacadeSegment: {str(e)}")
                else:
                    logger.warning(f"Failed to add event metadata to X-Ray segment: {str(e)}")

            # Now wrap the actual handler call with exception handling
            try:
                result = handler(event, context)
                return result
            except Exception as e:
                if segment:
                    try:
                        segment.add_exception(
                            exception=e, stack=traceback.extract_stack(), remote=False
                        )
                    except Exception as xray_e:
                        if "FacadeSegment" in str(xray_e):
                            logger.info(f"Cannot add exception to FacadeSegment: {str(xray_e)}")
                        else:
                            logger.warning(f"Failed to add exception to segment: {str(xray_e)}")
                raise

        return wrapper

    return decorator


def scrub_sensitive_data(data):
    """
    Scrub sensitive data from logs and traces

    Args:
        data (any): Data to scrub

    Returns:
        any: Scrubbed data
    """
    # If data is a dictionary, process it recursively
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Check if key might contain sensitive information
            if any(
                sensitive in key.lower()
                for sensitive in [
                    "password",
                    "secret",
                    "key",
                    "token",
                    "credential",
                    "auth",
                    "credit",
                    "card",
                    "cvv",
                    "ssn",
                    "social",
                    "security",
                ]
            ):
                result[key] = "<redacted>"
            else:
                result[key] = scrub_sensitive_data(value)
        return result
    # If data is a list, process each item
    elif isinstance(data, list):
        return [scrub_sensitive_data(item) for item in data]
    # Return primitives unchanged
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    # For other types, return a string representation
    else:
        return str(type(data))


def trace_s3_operations():
    """
    Patch S3 client to add tracing
    This is used in addition to the standard boto3 patching
    to add custom annotations for S3 operations
    """
    if not XRAY_AVAILABLE:
        return

    orig_s3_client = boto3.client

    def traced_s3_client(*args, **kwargs):
        client = orig_s3_client(*args, **kwargs)

        if args and args[0] == "s3":
            # Only trace S3 client operations

            # Get original operations
            orig_get_object = client.get_object
            orig_put_object = client.put_object
            orig_delete_object = client.delete_object

            # Patch get_object
            @wraps(orig_get_object)
            def traced_get_object(*args, **kwargs):
                subsegment = xray_recorder.begin_subsegment("S3.GetObject")
                try:
                    # Add annotations
                    if "Bucket" in kwargs:
                        subsegment.put_annotation("bucket", kwargs["Bucket"])
                    if "Key" in kwargs:
                        subsegment.put_annotation("key", kwargs["Key"])

                    # Execute original operation
                    response = orig_get_object(*args, **kwargs)

                    # Add metadata about the response
                    if response and "ContentLength" in response:
                        subsegment.put_metadata("content_length", response["ContentLength"], "s3")

                    return response
                except Exception as e:
                    subsegment.add_exception(e, traceback.extract_stack())
                    raise
                finally:
                    xray_recorder.end_subsegment()

            # Patch put_object
            @wraps(orig_put_object)
            def traced_put_object(*args, **kwargs):
                subsegment = xray_recorder.begin_subsegment("S3.PutObject")
                try:
                    # Add annotations
                    if "Bucket" in kwargs:
                        subsegment.put_annotation("bucket", kwargs["Bucket"])
                    if "Key" in kwargs:
                        subsegment.put_annotation("key", kwargs["Key"])

                    # Execute original operation
                    return orig_put_object(*args, **kwargs)
                except Exception as e:
                    subsegment.add_exception(e, traceback.extract_stack())
                    raise
                finally:
                    xray_recorder.end_subsegment()

            # Patch delete_object
            @wraps(orig_delete_object)
            def traced_delete_object(*args, **kwargs):
                subsegment = xray_recorder.begin_subsegment("S3.DeleteObject")
                try:
                    # Add annotations
                    if "Bucket" in kwargs:
                        subsegment.put_annotation("bucket", kwargs["Bucket"])
                    if "Key" in kwargs:
                        subsegment.put_annotation("key", kwargs["Key"])

                    # Execute original operation
                    return orig_delete_object(*args, **kwargs)
                except Exception as e:
                    subsegment.add_exception(e, traceback.extract_stack())
                    raise
                finally:
                    xray_recorder.end_subsegment()

            # Replace the methods with traced versions
            client.get_object = traced_get_object
            client.put_object = traced_put_object
            client.delete_object = traced_delete_object

        return client

    # Replace the boto3.client function with our traced version
    boto3.client = traced_s3_client


def trace_dynamodb_operations():
    """
    Add custom tracing for DynamoDB operations
    """
    if not XRAY_AVAILABLE:
        return

    orig_dynamodb_client = boto3.client

    def traced_dynamodb_client(*args, **kwargs):
        client = orig_dynamodb_client(*args, **kwargs)

        if args and args[0] == "dynamodb":
            # Only trace DynamoDB client operations

            # Get original operations
            orig_get_item = client.get_item
            orig_put_item = client.put_item
            orig_update_item = client.update_item
            orig_query = client.query

            # Patch get_item
            @wraps(orig_get_item)
            def traced_get_item(*args, **kwargs):
                subsegment = xray_recorder.begin_subsegment("DynamoDB.GetItem")
                try:
                    # Add annotations
                    if "TableName" in kwargs:
                        subsegment.put_annotation("table", kwargs["TableName"])

                    # Execute original operation
                    return orig_get_item(*args, **kwargs)
                except Exception as e:
                    subsegment.add_exception(e, traceback.extract_stack())
                    raise
                finally:
                    xray_recorder.end_subsegment()

            # Patch put_item
            @wraps(orig_put_item)
            def traced_put_item(*args, **kwargs):
                subsegment = xray_recorder.begin_subsegment("DynamoDB.PutItem")
                try:
                    # Add annotations
                    if "TableName" in kwargs:
                        subsegment.put_annotation("table", kwargs["TableName"])

                    # Execute original operation
                    return orig_put_item(*args, **kwargs)
                except Exception as e:
                    subsegment.add_exception(e, traceback.extract_stack())
                    raise
                finally:
                    xray_recorder.end_subsegment()

            # Patch update_item
            @wraps(orig_update_item)
            def traced_update_item(*args, **kwargs):
                subsegment = xray_recorder.begin_subsegment("DynamoDB.UpdateItem")
                try:
                    # Add annotations
                    if "TableName" in kwargs:
                        subsegment.put_annotation("table", kwargs["TableName"])

                    # Execute original operation
                    return orig_update_item(*args, **kwargs)
                except Exception as e:
                    subsegment.add_exception(e, traceback.extract_stack())
                    raise
                finally:
                    xray_recorder.end_subsegment()

            # Patch query
            @wraps(orig_query)
            def traced_query(*args, **kwargs):
                subsegment = xray_recorder.begin_subsegment("DynamoDB.Query")
                try:
                    # Add annotations
                    if "TableName" in kwargs:
                        subsegment.put_annotation("table", kwargs["TableName"])
                    if "IndexName" in kwargs:
                        subsegment.put_annotation("index", kwargs["IndexName"])

                    # Execute original operation
                    return orig_query(*args, **kwargs)
                except Exception as e:
                    subsegment.add_exception(e, traceback.extract_stack())
                    raise
                finally:
                    xray_recorder.end_subsegment()

            # Replace the methods with traced versions
            client.get_item = traced_get_item
            client.put_item = traced_put_item
            client.update_item = traced_update_item
            client.query = traced_query

        return client

    # Replace the boto3.client function with our traced version
    boto3.client = traced_dynamodb_client


# Initialize tracing for AWS services
if XRAY_AVAILABLE:
    trace_s3_operations()
    trace_dynamodb_operations()
