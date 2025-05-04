from setuptools import setup, find_packages

setup(
    name="music_generator",
    version="0.1.0",
    packages=find_packages(),
    description="Music Generator Agent for MoFA Framework",
    install_requires=[
        "beatoven-ai",
        "aiohttp"
    ],
    entry_points={
        "console_scripts": [
            "music_generator=agent.music_generator_agent:main",
        ],
    },
)