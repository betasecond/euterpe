from setuptools import setup, find_packages

setup(
    name="terminal_input",
    version="0.1.0",
    packages=find_packages(),
    description="Terminal Input Node for MoFA Framework",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "terminal_input=terminal_input:main",
        ],
    },
)