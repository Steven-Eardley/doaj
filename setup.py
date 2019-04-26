from setuptools import setup, find_packages
import sys

setup(
    name = 'doaj',
    version = '3.0.0',
    packages = find_packages(),
    install_requires = [
        "werkzeug",
        "Flask",
        "Flask-Login",
        "Flask-WTF",
        "Flask-Mail",
        "requests",
        "markdown",
        "gitpython",
        "lxml",
        "nose",
        "feedparser",
        "tzlocal",
        "pytz",
        "futures",
        "esprit",
        "nose",
        "unidecode",
        "Flask-Swagger",
        "flask-cors",
        "LinkHeader",
        #"universal-analytics-python",          #FIXME: no python 3 support
        "huey",
        "redis",
        "rstr",
        "freezegun",
        "responses",
        "Faker",
        "python-dateutil",  # something else already installs this, so just note we need it without an explicit version freeze
        # for deployment
        "gunicorn",
        "elastic-apm[flask]",
        "parameterized",
        "awscli",
        "boto3",
        "flask-debugtoolbar"
    ] + (["setproctitle"] if "linux" in sys.platform else []),
    url = 'https://doaj.org',
    author = 'Cottage Labs',
    author_email = 'us@cottagelabs.com',
    description = 'The Directory of Open Access Journals - website and directory software',
    license = 'Apache v2.0',
    classifiers = [
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
