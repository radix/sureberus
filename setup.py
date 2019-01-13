#!/usr/bin/env python
import setuptools

setuptools.setup(
    name="sureberus",
    description="Cerberus alternative",
    long_description=open('README.md').read(),
    url="http://github.com/radix/sureberus/",
    author="Christopher Armstrong",
    license="MIT",
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        ],
    packages=['sureberus'],
    install_requires=['six', 'attrs'],
    )
