import os
import os.path
from dataclasses import dataclass

from flask import render_template as flask_render_template
from flask import current_app, Blueprint, url_for, send_from_directory, abort
from jinja2.loaders import BaseLoader, TemplateNotFound, FileSystemLoader


#: The key under which the extension instance will be saved under the flask
#: app's `extension` dict.
EXTENSION_KEY = 'themer'
#: Prefix for all configuration keys.
CONFIG_PREFIX = 'THEMER_'
#: A magic value added to the start of paths returned from theme().
#: The presence of this value is what's used to decide if theming should handle
#: a template lookup. By default, it's a unicode snowman.
MAGIC_PATH_PREFIX = '\u2603'


def _current_themer():
    """Returns the currently active Themer instance."""
    try:
        return current_app.extensions[EXTENSION_KEY]
    except KeyError:
        raise RuntimeError(
            'Trying to use an uninitalized Themer, make sure you '
            'call init_app'
        )


@dataclass
class Theme:
    theme_loader: 'ThemeLoader'
    jinja_loader: BaseLoader
    name: str


class ThemeLoader:
    def themes(self):
        """
        Return a dict mapping theme names to `Theme` instances.
        """
        raise NotImplementedError

    def get_static(self, theme, path):
        """
        Return a static asset for the given theme and path.
        """
        raise NotImplementedError


class FileSystemThemeLoader(ThemeLoader):
    def __init__(self, app, path):
        self.app = app
        self.path = path

    def themes(self):
        themes = {}
        if os.path.exists(self.path):
            for name in os.listdir(self.path):
                path = os.path.join(self.path, name)
                if os.path.isdir(path):
                    themes[name] = Theme(
                        jinja_loader=FileSystemLoader(path),
                        theme_loader=self,
                        name=name
                    )

        return themes

    def get_static(self, theme, path):
        return send_from_directory(
            os.path.join(self.path, theme, 'static'),
            path
        )


class Themer:
    def __init__(self, *, app=None, loaders=None):
        self.loaders = []
        self.themes = {}
        self._theme_resolver = None

        if app is not None:
            self.init_app(app, loaders=loaders)

    def init_app(self, app, *, loaders=None):
        """Configure `app` to work with Flask-Themer and pre-populate the
        list of themes we know about."""
        app.extensions[EXTENSION_KEY] = self

        default_dir = app.config.setdefault(
            f'{CONFIG_PREFIX}DEFAULT_DIRECTORY',
            'themes'
        )

        app.add_template_global(lookup_theme_path, name='theme')
        app.add_template_global(lookup_static_theme_path, name='theme_static')
        app.register_blueprint(theme_blueprint)

        self.loaders = loaders or [
            FileSystemThemeLoader(app, os.path.join(
                app.root_path,
                default_dir
            ))
        ]

        for loader in self.loaders:
            self.themes.update(loader.themes())

    def current_theme_loader(self, loader):
        """Set the resolver to use when looking up the currently active
        theme.

        Ex:

            .. code-block:: python

                @themer.current_theme_loader
                def get_current_theme():
                    return current_user.settings.theme
        """
        self._theme_resolver = loader
        return loader

    @property
    def current_theme(self):
        """The currently active theme."""
        if not self._theme_resolver:
            raise RuntimeError(
                'No current theme resolver is registered, set one using '
                'current_theme_loader.'
            )

        return self._theme_resolver()


def render_template(path, *args, **kwargs):
    """Identical to flask's render_template, but loads from the active theme if
    one is available.
    """
    return flask_render_template(lookup_theme_path(path), *args, **kwargs)


def lookup_theme_path(path):
    """Given the path to a template, lookup the "real" path after resolving the
    active theme.
    """
    themer = _current_themer()
    return f'{MAGIC_PATH_PREFIX}/{themer.current_theme}/{path}'


def lookup_static_theme_path(path, **kwargs):
    themer = _current_themer()
    return url_for(
        f'{MAGIC_PATH_PREFIX}.static',
        theme=themer.current_theme,
        filename=path,
        **kwargs
    )


class _ThemeTemplateLoader(BaseLoader):
    """
    Flask provides two mechanisms for replacing the jinja loader,
    create_global_jinja_loader and jinja_loader.  However, these can't be
    overloaded by extensions. A Blueprint with a custom jinja_loader
    is used to get the same effect. This works because the default Flask
    template loader (DispatchTemplateLoader) looks at the app and *all*
    blueprint template folders when resolving a template path. This technique
    is borrowed from flask-themes.
    """
    def get_source(self, environment, template):
        if not template.startswith(MAGIC_PATH_PREFIX):
            raise TemplateNotFound(template)

        path = template[len(MAGIC_PATH_PREFIX) + 1:]
        try:
            theme, path = path.split('/', 1)
        except ValueError:
            # Much cheaper to catch the occasional error than it is to check
            # each time in the off chance we get here with a bad path.
            raise TemplateNotFound(template)

        themer = _current_themer()
        if theme in themer.themes:
            return themer.themes[theme].jinja_loader.get_source(
                environment,
                path
            )

        raise TemplateNotFound(template)


theme_blueprint = Blueprint(
    f'{MAGIC_PATH_PREFIX}',
    __name__
)
theme_blueprint.jinja_loader = _ThemeTemplateLoader()


@theme_blueprint.route('/static/<theme>/<path:filename>', endpoint='static')
def serve_static(theme, filename):
    themer = _current_themer()

    try:
        t = themer.themes[theme]
    except KeyError:
        abort(404)

    return t.theme_loader.get_static(theme, filename)
