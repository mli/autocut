from setuptools import setup, find_packages

requirements = [
    "srt",
    "moviepy",
    "opencc-python-reimplemented",
    "torchaudio",
    "parameterized",
    "openai-whisper @ git+https://github.com/openai/whisper.git",
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
