from setuptools import setup, find_packages

setup(
    name='riptide_cli',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click >= 7.0',
        # TODO
    ],
    entry_points='''
        [console_scripts]
        riptide=riptide.cli.main:cli
    ''',
)