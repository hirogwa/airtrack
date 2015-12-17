from setuptools import setup

setup(
    name='airtrack',
    version='0.1',
    install_requires=[
        'Click',
    ],
    packages=['airtrack'],
    entry_points='''
        [console_scripts]
        airtrack=airtrack.airtrack:cli
    ''',
)
