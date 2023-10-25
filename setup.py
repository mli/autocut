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
    name="autocut",
    install_requires=requirements,
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
