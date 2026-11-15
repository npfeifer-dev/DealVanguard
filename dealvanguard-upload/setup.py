from setuptools import find_packages, setup

setup(
    name="dealvanguard",
    version="0.2.0",
    description="Deal diligence and RevOps analytics: Claude extraction into validated schemas, DuckDB, Streamlit",
    author="npfeifer-dev",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.7.0",
        "anthropic>=0.40.0",
        "duckdb>=1.0.0",
        "pandas>=2.2.0",
        "streamlit>=1.50.0",
        "plotly>=5.22.0",
        "python-dotenv>=1.0.1",
    ],
    extras_require={"dev": ["pytest>=8.0.0"]},
)
