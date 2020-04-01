import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name="templatequery",
    version="0.1.3",
    author="Paul Donchenko",
    author_email="pjdonch@gmail.com",
    description="Convenient formatting for psycopg2 SQL queries",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pjdon/templatequery",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: "
        "GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=['psycopg2>=2.7.5']
)
