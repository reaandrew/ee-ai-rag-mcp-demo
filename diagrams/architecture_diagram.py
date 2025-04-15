#!/usr/bin/env python3
from diagrams import Diagram, Cluster
from diagrams.aws.storage import S3
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.analytics import ElasticsearchService as OpenSearchService
from diagrams.aws.integration import SNS
from diagrams.aws.ml import Comprehend, Textract
from diagrams.aws.security import KeyManagementService
from diagrams.aws.network import APIGateway, CloudFront
from diagrams.aws.management import CloudwatchLogs
from diagrams.aws.general import User

# Set diagram attributes
graph_attr = {
    "fontsize": "30",
    "bgcolor": "white",
    "pad": "0.75",
    "splines": "ortho",   # Orthogonal lines with right angles
    "fontname": "Sans-Serif",
    "rankdir": "LR",      # Left to Right layout
    "nodesep": "0.6",     # Increase space between nodes
    "ranksep": "0.8",     # Increase space between ranks
    "concentrate": "true" # Merge edges going to same direction
}

with Diagram("EE AI RAG MCP Demo Architecture", 
             show=True, 
             filename="ee_ai_rag_mcp_architecture",
             outformat="png", 
             graph_attr=graph_attr,
             direction="LR"):  # Left to Right direction

    # User and Client layer
    with Cluster("User Layer"):
        user = User("User")
        cf = CloudFront("CloudFront\nDistribution")
        ui_bucket = S3("UI\nS3 Bucket")
        
        user >> cf >> ui_bucket

    # API Layer    
    with Cluster("API Layer"):
        api = APIGateway("API Gateway")
        auth = Lambda("Auth\nAuthorizer")
        policy_search = Lambda("Policy\nSearch")
        kms = KeyManagementService("Token\nSigning Key")
        
        user >> api >> policy_search
        api >> auth
        auth >> kms

    # Document Processing Pipeline with clear subgroups
    with Cluster("Document Processing Pipeline"):
        with Cluster("Storage"):
            raw_pdfs = S3("Raw PDFs\nBucket")
            extracted_text = S3("Extracted Text\nBucket")
            chunked_text = S3("Chunked Text\nBucket")
        
        with Cluster("Processing Functions"):
            extractor = Lambda("Text\nExtractor")
            chunker = Lambda("Text\nChunker") 
            vector_gen = Lambda("Vector\nGenerator")
        
        with Cluster("Status and Tracking"):
            doc_status = Lambda("Document\nStatus")
            doc_tracking = Lambda("Document\nTracking")
            sns_topic = SNS("Document\nIndexing Topic")
        
        with Cluster("External Services"):
            textract = Textract("AWS Textract")
            bedrock = Comprehend("AWS Bedrock")
        
        # Primary data flow
        user >> raw_pdfs
        raw_pdfs >> extractor
        extractor >> textract
        extractor >> extracted_text
        
        extracted_text >> chunker
        chunker >> chunked_text
        
        chunked_text >> vector_gen
        vector_gen >> bedrock
        
        # Notification and status flow
        chunker >> sns_topic
        vector_gen >> sns_topic
        sns_topic >> doc_tracking
        api >> doc_status

    # Storage Layer
    with Cluster("Storage Layer"):
        opensearch = OpenSearchService("OpenSearch\nVector Store")
        tracking_db = Dynamodb("Document\nTracking DB")
        
        vector_gen >> opensearch
        policy_search >> opensearch
        doc_status >> tracking_db
        doc_tracking >> tracking_db
        policy_search >> bedrock