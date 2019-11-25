import pathlib
from setuptools import setup
import ctyparser.__info__ as info

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name=info.__project__,
    version=info.__version__,
    description=info.__summary__,
    long_description=README,
    long_description_content_type="text/markdown",
    url=info.__webpage__,
    author=info.__author__,
    author_email=info.__email__,
    license=info.__license__,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Communications :: Ham Radio",
    ],
    packages=["ctyparser"],
    package_data={
        "ctyparser": ["py.typed"]
    },
    install_requires=["feedparser", "requests"],
)
