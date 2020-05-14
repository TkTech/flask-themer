from pathlib import Path

import pytest
from flask import Flask
from jinja2 import TemplateNotFound

from flask_themer import (
    Themer,
    FileSystemThemeLoader,
    render_template,
    ThemeLoader,
    lookup_static_theme_path,
    MAGIC_PATH_PREFIX
)


@pytest.fixture
def app():
    app = Flask(
        'testing',
        template_folder=Path('tests') / 'data' / 'templates'
    )
    app.config['SERVER_NAME'] = 'testing'

    themer = Themer(app, loaders=[
        FileSystemThemeLoader(Path('tests') / 'data')
    ])
    themer.current_theme_loader(lambda: 'test_theme')

    with app.app_context():
        yield app


def test_loading_from_disk(app):
    """Ensure the simple case of finding a theme directory and reading a
    template from it."""
    assert render_template('test.html') == 'This is a test.'


def test_fallback(app):
    """Ensure we fall back to the Flask template resolution when a template is
    missing from a theme."""
    assert render_template('fallback.html') == 'This is a fallback template.'


def test_filter(app):
    """Ensure we can filter directories."""
    app = Flask('testing')

    themer = Themer(app, loaders=[
        FileSystemThemeLoader(
            Path('tests') / 'data',
            filter=lambda path: not path.name.startswith('_')
        )
    ])

    assert '_excluded_theme' not in themer.themes


def test_interface():
    loader = ThemeLoader()

    with pytest.raises(NotImplementedError):
        loader.themes

    with pytest.raises(NotImplementedError):
        loader.get_static('', '')


def test_static(app):
    """Ensure we can get a static file from the theme or fail reasonably if
    it's missing."""
    static_route = lookup_static_theme_path('static.txt')
    assert static_route == 'http://testing/static/test_theme/static.txt'

    with app.test_client() as client:
        rv = client.get(static_route)
        assert rv.data.strip() == b'This is a static asset test.'

        rv = client.get('http://testing/static/fake_theme/fake.txt')
        assert rv.status_code == 404


def test_bad_template_path(app):
    """Ensure we handle bad paths ending up in our blueprint."""
    with pytest.raises(TemplateNotFound):
        render_template(f'{MAGIC_PATH_PREFIX}/')
