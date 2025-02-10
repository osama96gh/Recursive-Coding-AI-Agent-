from setuptools import setup, find_packages

setup(
    name="recursive-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain>=0.1.0",
        "langchain-core>=0.1.10",
        "langchain-community>=0.0.10",
        "langgraph>=0.0.10",
        "python-dotenv>=1.0.0",
        "openai>=1.10.0",
        "pytest>=7.4.0",
        "pytest-asyncio>=0.23.0"
    ]
)
