from django.http import HttpResponse
from fluent_pages.extensions import PageTypePlugin, page_type_pool
from fluent_pages.pagetypes.textfile.models import TextFile


class TextFilePlugin(PageTypePlugin):
    model = TextFile

    def get_response(self, request, textfile, **kwargs):
        content_type = textfile.content_type
        if content_type in TextFile.UTF8_TYPES:
            content_type += '; charset=utf-8'  # going to enforce this.

        return HttpResponse(
            content=textfile.content,
            content_type=content_type,
        )

page_type_pool.register(TextFilePlugin)
