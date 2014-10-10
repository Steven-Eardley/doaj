from setuptools import setup, find_packages
import sys

setup(
    name = 'portality',
    version = '0.8.0',
    packages = find_packages(),
    install_requires = [
        "werkzeug==0.8.3",
        "Flask==0.9",
        "Flask-Login==0.1.3",
        "Flask-WTF==0.8.3",
        "Flask-Mail==0.9.0",
        "requests==1.1.0",
        "markdown",
        "gitpython",
        "lxml",
        "feedparser",
        "tzlocal",
        "futures==2.1.6",
        "esprit==0.0.2",
        "nose==1.3.4",
        "behave==1.2.4",
        "selenium==2.43.0",
        # for deployment
        "gunicorn",
        "newrelic",
    ] + (["setproctitle"] if "linux" in sys.platform else []),

    url = 'http://cottagelabs.com/',
    author = 'Cottage Labs',
    author_email = 'us@cottagelabs.com',
    description = 'A web API layer over an ES backend, with various useful views',
    license = 'Copyheart',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: Copyheart',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
