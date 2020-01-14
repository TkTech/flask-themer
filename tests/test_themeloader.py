from pathlib import Path

import pytest
from flask import Flask

from flask_themer import (
    Themer,
    FileSystemThemeLoader,
    render_template
)


@pytest.fixture
def app():
    app = Flask(
        'testing',
        template_folder=Path('tests') / 'data' / 'templates'
    )

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
