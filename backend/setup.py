"""Setup configuration for Adaptix Admin backend."""
from setuptools import find_packages, setup

setup(
    name="adaptix-admin-backend",
    version="1.0.0",
    description="Production-grade Adaptix Admin governance, feature-flag, audit, legal-hold, and AI policy system",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.115,<1",
        "uvicorn>=0.30,<1",
        "pydantic>=2.7,<3",
    ],
)
