from setuptools import setup, find_packages

setup(
    name="dealvanguard",
    version="0.1.0",
    description="Enterprise Deal Diligence & RevOps AI Engine",
    author="npfeifer-dev",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0.0",
        "anthropic>=0.18.0",
        "duckdb>=0.9.0",
        "polars>=0.20.0",
        "pandas>=2.0.0",
        "streamlit>=1.30.0",
        "plotly>=5.18.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": ["pytest>=8.0.0", "pytest-mock>=3.12.0"],
    },
)