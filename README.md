# ![Riptide](https://riptide-docs.readthedocs.io/en/latest/_images/logo.png)

[<img src="https://img.shields.io/github/actions/workflow/status/theCapypara/riptide-cli/build.yml" alt="Build Status">](https://github.com/theCapypara/riptide-cli/actions)
[<img src="https://readthedocs.org/projects/riptide-docs/badge/?version=latest" alt="Documentation Status">](https://riptide-docs.readthedocs.io/en/latest/)
[<img src="https://img.shields.io/pypi/v/riptide-cli" alt="Version">](https://pypi.org/project/riptide-cli/)
[<img src="https://img.shields.io/pypi/dm/riptide-cli" alt="Downloads">](https://pypi.org/project/riptide-cli/)
<img src="https://img.shields.io/pypi/l/riptide-cli" alt="License (MIT)">
<img src="https://img.shields.io/pypi/pyversions/riptide-cli" alt="Supported Python versions">

Riptide is a set of tools to manage development environments for web applications.
It's using container virtualization tools, such as [Docker](https://www.docker.com/)
to run all services needed for a project.

Its goal is to be easy to use by developers.
Riptide abstracts the virtualization in such a way that the environment behaves exactly
as if you were running it natively, without the need to install any other requirements
the project may have.

Riptide consists of a few repositories, find the
entire [overview](https://riptide-docs.readthedocs.io/en/latest/development.html) in the documentation.

## CLI Application

This repository contains the CLI application for Riptide. The library used for the CLI
is [Click](https://click.palletsprojects.com/en/7.x/).

The CLI application uses the Riptide lib package to manage files and to communicate with the container engine backend.

It can be installed via pip by installing `riptide-cli`.

## Documentation

The complete documentation for Riptide can be found at [Read the Docs](https://riptide-docs.readthedocs.io/en/latest/).
