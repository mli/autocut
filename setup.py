from setuptools import setup, find_packages
import os 

requirements = [
    'srt',
    'moviepy',
]

with open(os.path.dirname(__file__)+'/autocut/__init__.py') as f:
    for l in f.readlines():
        if '__version__' in l:
            exec(l)
            break

setup(
    name='autocut',
    version=__version__,
    install_requires=requirements,
    setup_requires=['sphinx>=2.2.1'],
    python_requires='>=3.8',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'autocut = autocut.main:main',
        ]
    },
)