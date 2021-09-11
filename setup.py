from setuptools import setup

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='flask-themer',
    version='1.4.3',
    description='Simple theme mechanism for Flask',
    author='Tyler Kennedy',
    author_email='tk@tkte.ch',
    url='https://github.com/tktech/flask-themer',
    long_description=long_description,
    long_description_content_type='text/markdown',
    py_modules=['flask_themer'],
    install_requires=[
        'flask'
    ],
    tests_require=[
        'pytest',
        'pytest-cov'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    keywords=[
        'flask',
        'themes',
        'jinja2'
    ]
)
