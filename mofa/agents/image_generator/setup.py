from setuptools import setup, find_packages

setup(
    name="image_generator",
    version="0.1.0",
    packages=find_packages(),
    description="Image Generator Agent for MoFA Framework",
    install_requires=[
        "klingdemo",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "image_generator=agent.image_generator_agent:main",
        ],
    },
)