from fluent_pages.extensions import PageTypePlugin, page_type_pool
from fluent_pages.pagetypes.fluentpage.models import FluentPage
from fluent_pages.pagetypes.fluentpage.admin import FluentPageAdmin


class FluentPagePlugin(PageTypePlugin):
    model = FluentPage
    model_admin = FluentPageAdmin

    def get_render_template(self, request, fluentpage, **kwargs):
        return fluentpage.layout.template_path


page_type_pool.register(FluentPagePlugin)
