from setuptools import setup

setup(
    name='airtrack',
    version='0.1',
    py_modules=['airtrack'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        airtrack=airtrack:cli
    ''',
)
