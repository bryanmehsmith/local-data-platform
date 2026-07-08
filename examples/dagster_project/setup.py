from setuptools import find_packages, setup

setup(
    name="local_data_platform",
    packages=find_packages(exclude=["local_data_platform_tests"]),
    install_requires=[
        "dagster",
        "dagster-dbt",
        "trino",
        "dbt-trino",
        "boto3",
        "requests",
        "qdrant-client",
    ],
)
