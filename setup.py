from setuptools import setup, find_packages

# README read-in
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in

setup(
    name='riptide-cli',
    version='0.1.2',
    packages=find_packages(),
    package_data={'riptide_cli': ['shell/*']},
    description='Tool to manage development environments for web applications using containers - CLI-Application',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/Parakoopa/riptide-cli/',
    author='Marco "Parakoopa" Köpcke',
    license='MIT',
    install_requires=[
        'riptide-lib >= 0.1, < 0.2',
        'Click >= 7.0',
        'colorama >= 0.4',
        'click-help-colors >= 0.5',
        'tqdm >= 4.29',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points='''
        [console_scripts]
        riptide=riptide_cli.main:cli
    ''',
    # Scripts for the shell integration, meant to be sourced.
    scripts=['riptide_cli/shell/riptide.hook.bash',
             'riptide_cli/shell/riptide.hook.zsh',
             'riptide_cli/shell/riptide.hook.common.sh']
)
