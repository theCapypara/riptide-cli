__version__ = '0.9.0'

# README read-in
from os import path

from setuptools import setup, find_packages

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in

setup(
    name='riptide-cli',
    version=__version__,
    packages=find_packages(),
    package_data={'riptide_cli': ['shell/*']},
    description='Tool to manage development environments for web applications using containers - CLI-Application',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/theCapypara/riptide-cli/',
    author='Marco "theCapypara" Köpcke',
    license='MIT',
    install_requires=[
        'riptide-lib >= 0.9, < 0.10',
        'Click >= 7.0, < 9.0',
        'colorama >= 0.4',
        'click-help-colors >= 0.5',
        'tqdm >= 4.38',
        'packaging'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    entry_points='''
        [console_scripts]
        riptide=riptide_cli.__main__:cli
        riptide_upgrade=riptide_cli.self_updater:update
    ''',
    # Scripts for the shell integration, meant to be sourced.
    scripts=['riptide_cli/shell/riptide.hook.bash',
             'riptide_cli/shell/riptide.hook.zsh',
             'riptide_cli/shell/riptide.hook.common.sh']
)
