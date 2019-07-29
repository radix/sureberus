#!/usr/bin/env python
import setuptools

setuptools.setup(
    name="sureberus",
    version="0.12.0",
    description="Validation & transformation.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    project_urls={
        "Source Code": "https://github.com/radix/sureberus/",
        "Documentation": "https://radix.github.io/sureberus/",
    },
    author="Christopher Armstrong",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
    packages=["sureberus"],
    install_requires=["six", "attrs"],
)
