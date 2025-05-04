from setuptools import setup, find_packages

setup(
    name="video_generator",
    version="0.1.0",
    packages=find_packages(),
    description="Video Generator Agent for MoFA Framework",
    install_requires=[
        "klingdemo",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "video_generator=agent.video_generator_agent:main",
        ],
    },
)