from setuptools import setup, find_packages
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="kag-langgraph",
    version="0.1.0",
    author="KAG-LangGraph Project",
    author_email="contact@example.com",
    description="A portable knowledge graph construction pipeline using LangGraph",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/kag-langgraph",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langgraph>=0.0.40",
        "langgraph-cli[inmem]>=0.4.0",
        "langchain-core>=0.1.0",
        "langchain-openai>=0.1.0",
        "pypdf>=3.0.0",
        "python-docx>=0.8.11",
        "sentence-transformers>=2.2.0",
        "openai>=1.0.0",
        "pandas>=1.5.0",
        "numpy>=1.24.0",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        "click>=8.0.0",
        "tqdm>=4.65.0",
        "requests>=2.31.0",
        "nltk>=3.8.0",
        # LangSmith tracing
        "langsmith>=0.1.0",
        "langchain>=0.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
        "server": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "python-multipart>=0.0.6",
        ],
        "neo4j": ["neo4j>=5.0.0"],
        "ollama": ["ollama>=0.1.7"],
    },
    entry_points={
        "console_scripts": [
            "kag-langgraph=kag_langgraph.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "kag_langgraph": ["examples/*.yaml", "examples/*.py"],
    },
)