from setuptools import setup, find_packages

requirements = [
    "ffmpeg-python",
    "moviepy",
    "openai-whisper",
    "opencc-python-reimplemented",
    "parameterized",
    "pydub",
    "srt",
    "torchaudio",
    "tqdm",
]


setup(
    name="autocut-sub",
    install_requires=requirements,
    url="https://github.com/mli/autocut",
    project_urls={
        "source": "https://github.com/mli/autocut",
    },
    license="Apache License 2.0",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    extras_require={
        "all": ["openai", "faster-whisper"],
        "openai": ["openai"],
        "faster": ["faster-whisper"],
    },
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "autocut = autocut.main:main",
        ]
    },
)
