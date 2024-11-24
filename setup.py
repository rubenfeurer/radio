from setuptools import setup, find_packages

setup(
    name="internetradio",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'python-vlc',
        'RPi.GPIO',
        'Flask',
        'tomli',
        'requests'
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-mock',
            'pytest-cov'
        ]
    }
) 