import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name="ctyparser",
    version="1.0.0",
    description="CTY.DAT parser for amateur radio",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/classabbyamp/ctyparser",
    author="classabbyamp, 0x5c",
    author_email="me@kb6.ee",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["ctyparser"],
    include_package_data=True,
    install_requires=["feedparser"],
)
