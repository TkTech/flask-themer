from flask import Flask, url_for

from flask_themer import Themer, EXTENSION_KEY, MAGIC_PATH_PREFIX


def test_jinja_env():
    """Ensure that we properly configure the Jinja environment."""
    app = Flask('testing')
    themer = Themer(app, loaders=[])

    assert app.extensions[EXTENSION_KEY] is themer
    assert 'theme' in app.jinja_env.globals
    assert 'theme_static' in app.jinja_env.globals


def test_static_path():
    """Ensure we can generate a path to a static resource."""
    app = Flask('testing')
    # Needed to generate urls without a request context.
    app.config['SERVER_NAME'] = 'testing'
    Themer(app, loaders=[])

    with app.app_context():
        assert url_for(
            f'{MAGIC_PATH_PREFIX}.static',
            theme='testing',
            filename='testing.static',
            _scheme='http',
            _external=True
        ) == 'http://testing/static/testing/testing.static'
