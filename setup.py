from setuptools import setup, find_packages

setup(
    name='riptide_cli',
    version='0.1',
    packages=find_packages(),
    description= 'TODO',  # TODO
    long_description= 'TODO',  # TODO
    install_requires=[
        'riptide_lib == 0.1',
        'Click >= 7.0',
        'colorama >= 0.4',
        'click-help-colors >= 0.5',
        'tqdm >= 4.29',
    ],
    # TODO
    classifiers=[
        'Programming Language :: Python',
    ],
    entry_points='''
        [console_scripts]
        riptide=riptide_cli.main:cli
    ''',
)