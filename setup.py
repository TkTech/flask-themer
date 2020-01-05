from setuptools import setup

setup(
    name='flask-themer',
    version='1.0.0',
    description='Simple theme mechanism for Flask',
    author='Tyler Kennedy',
    author_email='tk@tkte.ch',
    url='https://github.com/tktech/flask-themer',
    install_requires=[
        'flask'
    ],
    tests_require=[
        'pytest'
    ],
    py_modules=[
        'flask_themer'
    ]
)
