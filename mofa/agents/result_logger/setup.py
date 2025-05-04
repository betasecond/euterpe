from setuptools import setup, find_packages

setup(
    name="result_logger",
    version="0.1.0",
    packages=find_packages(),
    description="Result Logger Agent for MoFA Framework",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "result_logger=agent.result_logger_agent:main",
        ],
    },
)