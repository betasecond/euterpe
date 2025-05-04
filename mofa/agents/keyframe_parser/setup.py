from setuptools import setup, find_packages

setup(
    name="keyframe_parser",
    version="0.1.0",
    packages=find_packages(),
    description="Keyframe Parser Agent for MoFA Framework",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "keyframe_parser=agent.keyframe_parser_agent:main",
        ],
    },
)