from setuptools import setup, find_packages

requirements = [
    "srt",
    "moviepy",
    "opencc-python-reimplemented",
    "streamlit",
    "numpy",
    "torchaudio",
    "parameterized",
    "openai-whisper",
    "tqdm",
]


setup(
    name="autocut",
    install_requires=requirements,
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "autocut = autocut.main:main",
            "autocut-gui = autocut.interface.main:main",
        ]
    },
)
