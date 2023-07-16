from setuptools import setup, find_packages

requirements = [
    "srt",
    "moviepy",
    "opencc-python-reimplemented",
    "torchaudio",
    "parameterized",
    "openai-whisper==20230314",
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
