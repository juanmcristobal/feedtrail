#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.md') as history_file:
    history = history_file.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    author="Juan Manuel Cristóbal Moreno",
    author_email='juanmcristobal@gmail.com',
    python_requires='>=3.10',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    description="Feed Tracking and Retrieval Abstraction Interface Layer",
    install_requires=required,
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='feedtrail',
    name='feedtrail',
    packages=find_packages(include=['feedtrail', 'feedtrail.*']),
    project_urls={
        'Repository': 'https://github.com/juanmcristobal/feedtrail',
        'Issues': 'https://github.com/juanmcristobal/feedtrail/issues',
    },
    url='https://github.com/juanmcristobal/feedtrail',
    version='0.1.0',
    zip_safe=False,
)
