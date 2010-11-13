"""
The manager class for the Enterprise-CMS models
"""
from django.db import models
from django.http import Http404
from vdboor.managers import DecoratorManager


class CmsObjectManager(DecoratorManager):
    """
    Extra methods attached to ```CmsObjects.objects```
    """

    def get_for_path_or_404(self, path):
        """
        Return the CmsObject for the given path.

        Raises a Http404 error when the object is not found.
        """
        try:
            return self.get_for_path(path)
        except self.model.DoesNotExist:
            raise Http404("No published CmsObject found for the path: '%s'" % path)


    def get_for_path(self, path):
        """
        Return the CmsObject for the given path.

        Raises CmsObject.DoesNotExist when the item is not found.
        """
        stripped = path.strip('/')
        stripped = stripped and u'/%s/' % stripped or '/'
        return self.published().get(_cached_url=stripped)


    def published(self):
        """
        Return only published pages
        """
        from ecms.models import CmsObject   # the import can't be globally, that gives a circular dependency
        return self.get_query_set().filter(status=CmsObject.PUBLISHED)


    def in_navigation(self):
        """
        Return only pages in the navigation.
        """
        return self.published().filter(in_navigation=True)


    def toplevel_navigation(self, current_page=None):
        """
        Return all toplevel items.

        When current_page is passed, the object values such as 'is_current' will be set. 
        """
        items = self.in_navigation().filter(parent__isnull=True)
        if current_page:
            items = _mark_current(items, current_page)
        return items



# Implemented as method, to avoid overwriting the QuerySet once again.
def _mark_current(qs, current_page):
    """
    Mark the given page as "is_current" in the resulting set.
    """
    current_id = current_page.id

    def add_prop(obj):
        obj.is_current = (obj.id == current_id)

    return qs.decorate(add_prop)
