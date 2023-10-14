from setuptools import setup, find_packages

requirements = [
    "ffmpeg",
    "moviepy",
    "openai",
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
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "autocut = autocut.main:main",
        ]
    },
)
