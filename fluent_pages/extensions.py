"""
Special classes to extend the module; e.g. page type plugins.

The extension mechanism is provided for projects that benefit
from a tighter integration then the Django URLconf can provide.

The API uses a registration system.
While plugins can be easily detected via ``__subclasses__()``, the register approach is less magic and more explicit.
Having to do an explicit register ensures future compatibility with other API's like reversion.
"""
from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse
from django.utils.importlib import import_module
from fluent_pages.admin import UrlNodeAdmin
from fluent_pages.models import UrlNode

__all__ = ('PageTypePlugin', 'plugin_pool')



class PageTypePlugin(object):
    """
    The base class for a page type plugin.

    To create a new plugin, derive from this class and call :func:`plugin_pool.register <PluginPool.register>` to enable it.
    """
    __metaclass__ = forms.MediaDefiningClass

    # -- Settings to override:

    #: The model to use, must derive from :class:`fluent_contents.models.UrlNode`.
    model = None

    #: The modeladmin instance to customize the screen.
    model_admin = UrlNodeAdmin

    #: The template to render the frontend HTML output.
    render_template = None

    #: The class to use by default for the response
    response_class = TemplateResponse


    @property
    def verbose_name(self):
        """
        The title for the plugin, by default it reads the ``verbose_name`` of the model.
        """
        return self.model._meta.verbose_name


    @property
    def type_name(self):
        """
        Return the classname of the model, this is mainly provided for templates.
        """
        return self.model.__name__


    def get_model_instances(self):
        """
        Return the model instances the plugin has created.
        """
        return self.model.objects.all()


    def get_response(self, request, page, **kwargs):
        """
        Return the Django response for the page.
        """
        render_template = self.get_render_template(request, page, **kwargs)
        if not render_template:
            raise ImproperlyConfigured("{0} should either provide a definition of 'render_template' or an implementation of 'get_response()'".format(self.__class__.__name__))

        context = self.get_context(request, page, **kwargs)
        return self.response_class(
            request = request,
            template = render_template,
            context = context,
        )


    def get_render_template(self, request, page, **kwargs):
        """
        Return the template to render for the specific `page` or `request`,
        By default it uses the ``render_template`` attribute.
        """
        return self.render_template


    def get_context(self, request, page, **kwargs):
        """
        Return the context to use in the template defined by ``render_template`` (or :func:`get_render_template`).
        By default, it returns the model instance as ``instance`` field in the template.
        """
        return {
            'page': page,
            'site': page.parent_site,
        }



# -------- Some utils --------

def _import_apps_submodule(submodule):
    """
    Look for a submodule is a series of packages, e.g. ".pagetype_plugins" in all INSTALLED_APPS.
    """
    for app in settings.INSTALLED_APPS:
        try:
            import_module('.' + submodule, app)
        except ImportError, e:
            if submodule not in str(e):
                raise   # import error is a level deeper.
            else:
                pass


# -------- API to access plugins --------

class PageTypeAlreadyRegistered(Exception):
    """
    Raised when attempting to register a plugin twice.
    """
    pass


class PageTypeNotFound(Exception):
    """
    Raised when the plugin could not be found in the rendering process.
    """
    pass


class PageTypePool(object):
    """
    The central administration of plugins.
    """

    def __init__(self):
        self.plugins = {}
        self.plugin_for_model = {}
        self.detected = False
        self.admin_site = admin.AdminSite()

    def register(self, plugin):
        """
        Make a page type plugin known by the CMS.

        :param plugin: The plugin class, deriving from :class:`PageTypePlugin`.

        The plugin will be instantiated, just like Django does this with :class:`~django.contrib.admin.ModelAdmin` classes.
        If a plugin is already registered, this will raise a :class:`PluginAlreadyRegistered` exception.
        """
        # Duct-Typing does not suffice here, avoid hard to debug problems by upfront checks.
        assert issubclass(plugin, PageTypePlugin), "The plugin must inherit from `PageTypePlugin`"
        assert plugin.model, "The plugin has no model defined"
        assert issubclass(plugin.model, UrlNode), "The plugin model must inherit from `ContentItem`"

        name = plugin.__name__
        if name in self.plugins:
            raise PageTypeAlreadyRegistered("[%s] a plugin with this name is already registered" % name)

        # Make a single static instance, similar to ModelAdmin.
        plugin_instance = plugin()
        self.plugins[name] = plugin_instance
        self.plugin_for_model[plugin.model] = name       # Track reverse for rendering

        # Instantiate model admin
        self.admin_site.register(plugin.model, plugin.model_admin)


    def get_plugins(self):
        """
        Return the list of all plugin instances which are loaded.
        """
        self._import_plugins()
        return self.plugins.values()


    def get_model_classes(self):
        """
        Return all :class:`~fluent_contents.models.ContentItem` model classes which are exposed by plugins.
        """
        self._import_plugins()
        return [plugin.model for plugin in self.plugins.values()]


    def get_plugin_by_model(self, model_class):
        """
        Return the corresponding plugin for a given model.
        """
        self._import_plugins()                   # could happen during rendering that no plugin scan happened yet.
        assert issubclass(model_class, UrlNode)  # avoid confusion between model instance and class here!

        try:
            name = self.plugin_for_model[model_class]
        except KeyError:
            raise PageTypeNotFound("No plugin found for model '{0}'.".format(model_class.__name__))
        return self.plugins[name]


    def get_model_admin(self, model_class):
        """
        Access the model admin object instantiated for the plugin.
        """
        self._import_plugins()                   # could happen during rendering that no plugin scan happened yet.
        assert issubclass(model_class, UrlNode)  # avoid confusion between model instance and class here!

        try:
            return self.admin_site._registry[model_class]
        except KeyError:
            raise PageTypeNotFound("No ModelAdmin found for model '{0}'.".format(model_class.__name__))


    def _import_plugins(self):
        """
        Internal function, ensure all plugin packages are imported.
        """
        if self.detected:
            return
        _import_apps_submodule("page_type_plugins")
        self.detected = True

#: The global plugin pool, a instance of the :class:`PluginPool` class.
page_type_pool = PageTypePool()
