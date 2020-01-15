![PyPI](https://img.shields.io/pypi/v/flask-themer?style=flat-square)
![PyPI - License](https://img.shields.io/pypi/l/flask-themer?style=flat-square)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/TkTech/flask-themer/Run%20tests?style=flat-square)


# Flask-Themer

Simple theme support for flask apps.

Flask-Themer is inspired by the (seemingly) abandoned [flask-themes][] project,
but has been written from scratch for py3.7+ (or 3.6 with the dataclasses
backport). However it is _not_ immediately compatible with flask-themes and
does not seek to be. Flask-Themer tries to have little opinion on how you
actually structure your project and its themes and does not require a
particular metadata format/file.

Flask-Themer releases follow [Semantic Versioning][semver].
Flask-Themer has 100% test coverage and considers it an error to fall below
100%.

## Installation

Install the latest release from [PyPi][]:

```
pip install flask-themer
```

or get the latest development version from github:

```
git clone https://github.com/TkTech/flask-themer.git
cd flask-themer
python setup.py develop
```

## Quickstart


Flask-Themer usage is usually very basic, and once setup you likely won't need
to touch it again. Lets do a quickstart. Notice how we import `render_template`
from `flask_themer` instead of `flask`.


Our `app.py` looks like this:

```python
from flask import Flask
from flask_themer import Themer, render_template

app = Flask(__name__)
themer = Themer(app)


@themer.current_theme_loader
def get_current_theme():
    # This is where you would look up the current user's theme if one was
    # logged in, for example.
    return 'default'

@app.route('/')
def hello_world():
    return render_template('hello.html')
```

And next to it we have a directory called `themes` with a directory called
`default` inside of it. Our `themes/default/hello.html` looks like this:


```jinja2
Hello world!
```

That's it! By default Flask-Themer will look for a `themes` directory next to
your project and assume all the directories inside of it are themes. You can
change what directory it looks for with `THEMER_DEFAULT_DIRECTORY`, or specify
the template loaders explicitly to overwrite the default:

```python
from flask_themer import Themer, FileSystemThemeLoader

app = Flask(__name__)
themer = Themer(app, loaders=[
    FileSystemThemeLoader(app, os.path.join(
        app.root_path,
        'also_themes'
    ))
])
```

## Using Themes From Templates

Two template globals are added once Flask-Themer is setup, `theme()` and
`theme_static()` (just like flask-themes). These methods look up the currently
active theme and look for the given path in that theme, returning a special
path that Jinja can use to load it.

```jinja2
{% extends theme("base.html") %}

{% block header %}
    {{ super() }}
    <link rel="stylesheet" href="{{ theme_static("bootstrap.css") }}">
{% endblock %}
```

## Theme Loaders

_Theme_ loaders are the mechanism by which Flask-Themer discovers what themes
are available. You can create a custom loader to get themes from a ZIP file, or
a database for example. Usually if you create a new `ThemeLoader` you'll also
need to create a new Jinja [_template_ loader][loader] so Jinja knows how to
read individual templates. Lets do a very minimal example that loads just a
single theme from a ZIP file.


```python
from zipfile import ZipFile
from flask_themer import ThemeLoader, Theme
from jinja2.loaders import BaseLoader, TemplateNotFound

class ZipFileTemplateLoader(BaseLoader):
    def __init__(self, *args, archive, **kwargs):
        super().__init__(*args, **kwargs)
        self.archive = archive

    def get_source(self, environment, template):
        try:
            return (self.archive.read(template), None, False)
        except KeyError:
            raise TemplateNotFound(template)


class ZipFileThemeLoader(ThemeLoader):
    def __init__(self, path_to_zip):
        self.archive = ZipFile(path_to_zip)

    @property
    def themes(self):
        yield Theme(
            name='my_dumb_theme',
            theme_loader=self,
            jinja_loader=ZipFileTemplateLoader(archive=self.archive),
        )

    def get_static(self, theme, path):
        return self.archive.read(path)
```

And then to use our new loaders we update our previous example:

```python
...
themer = Themer(app, loaders=[
    ZipFileThemeLoader('my_dumb_theme.zip')
])
...
```

Pretty simple right? You can see how we could easily create a loader to load
multiple themes from an archive, or load a user's customized theme from a
database.

[flask-themes]: https://github.com/maxcountryman/flask-themes
[pypi]: https://pypi.org/
[semver]: https://semver.org/
[loader]: https://jinja.palletsprojects.com/en/latest/api/#loaders
