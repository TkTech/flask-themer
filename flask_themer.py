from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterable, Callable, Union
from contextlib import contextmanager

from flask import render_template as flask_render_template
from flask import current_app, Blueprint, url_for, send_from_directory, abort
from jinja2 import TemplateNotFound
from jinja2.loaders import BaseLoader, FileSystemLoader


#: The key under which the extension instance will be saved under the flask
#: app's `extension` dict.
EXTENSION_KEY = 'themer'
#: Prefix for all configuration keys.
CONFIG_PREFIX = 'THEMER_'
#: A magic value added to the start of paths returned from theme().
#: The presence of this value is what's used to decide if theming should handle
#: a template lookup. By default, it's a unicode snowman.
MAGIC_PATH_PREFIX = '\u2603'


class ThemeError(Exception):
    pass


class NoThemeResolver(ThemeError):
    pass


class ThemerNotInitialized(ThemeError, RuntimeError):
    pass


@dataclass
class Theme:
    #: The `ThemeLoader` instance that created the Theme.
    theme_loader: 'ThemeLoader'
    #: A Jinja2 BaseLoader subclass that can load a template from the theme.
    jinja_loader: BaseLoader
    #: The name of the theme.
    name: str
    #: Any extra data for this theme. ThemeLoader implementers are free to use
    #: this in any way they want. For example, reading a YAML file with
    #: metadata and storing it here.
    data: dict = field(default_factory=dict)


class ThemeLoader:
    @property
    def themes(self) -> Iterable[Theme]:
        """
        Return a dict mapping theme names to `Theme` instances.
        """
        raise NotImplementedError

    def get_static(self, theme: str, path: str) -> bytes:
        """
        Return a static asset for the given theme and path.
        """
        raise NotImplementedError


class FileSystemThemeLoader(ThemeLoader):
    """A simple theme loader that assumes all sub-directories immediately under
    `path` are themes.
    """
    def __init__(self, path: Union[Path, str],
                 filter: Callable[[Path], bool] = None):
        #: The path the loader is searching for themes.
        self.path = Path(path)
        self._filter = filter

    @property
    def themes(self):
        themes = {}
        if self.path.exists():
            for child in self.path.iterdir():
                if not child.is_dir():
                    continue

                if self._filter and not self._filter(child):
                    continue

                yield Theme(
                    jinja_loader=FileSystemLoader(str(child)),
                    theme_loader=self,
                    name=child.name
                )

        return themes

    def get_static(self, theme, path):
        return send_from_directory(self.path / theme / 'static', path)


class Themer:
    def __init__(self, app=None, *, loaders=None):
        self.loaders = []
        self.themes = {}
        self._theme_resolver = None
        self._explicit_theme_stack = []

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
            FileSystemThemeLoader(Path(app.root_path) / default_dir)
        ]

        for loader in self.loaders:
            for theme in loader.themes:
                self.themes[theme.name] = theme

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
        if self._explicit_theme_stack:
            return self._explicit_theme_stack[-1]

        if not self._theme_resolver:
            raise NoThemeResolver(
                'No current theme resolver is registered, set one using '
                'current_theme_loader.'
            )

        return self._theme_resolver()


def render_template(path, *args, **kwargs):
    """Identical to flask's render_template, but loads from the active theme if
    one is available.
    """
    try:
        return flask_render_template(lookup_theme_path(path), *args, **kwargs)
    except TemplateNotFound:
        return flask_render_template(path, *args, **kwargs)


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


@contextmanager
def use_theme(theme):
    """Temporarily override the theme."""
    themer = _current_themer()

    try:
        themer._explicit_theme_stack.append(theme)
        yield
    finally:
        themer._explicit_theme_stack.pop()


def _current_themer() -> Themer:
    """Returns the currently active Themer instance."""
    try:
        return current_app.extensions[EXTENSION_KEY]
    except KeyError:
        raise ThemerNotInitialized(
            'Trying to use an uninitalized Themer, make sure you '
            'call init_app'
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
# Need to use setattr to shut up mypy, see:
# https://github.com/python/mypy/issues/2427
setattr(theme_blueprint, 'jinja_loader', _ThemeTemplateLoader())


@theme_blueprint.route('/_theme/<theme>/<path:filename>', endpoint='static')
def serve_static(theme, filename):
    themer = _current_themer()

    try:
        t = themer.themes[theme]
    except KeyError:
        abort(404)

    return t.theme_loader.get_static(theme, filename)
