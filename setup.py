from setuptools import setup, find_packages

setup(
    name="ee-ai-rag-mcp-demo",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "boto3>=1.28.0",
        "pyjwt>=2.6.0",
        "cryptography==36.0.0",
    ],
    description="Text extractor for PDFs stored in S3",
    author="Claude AI",
    author_email="claude@anthropic.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)