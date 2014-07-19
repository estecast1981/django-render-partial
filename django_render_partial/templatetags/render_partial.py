from django.core.urlresolvers import reverse, resolve
from django.template import Library, Node, TemplateSyntaxError, Variable
from django.conf import settings

register = Library()


class ViewNode(Node):
    def __init__(self, view_name, args, kwargs):
        self.view_name = view_name
        self.args = args
        self.kwargs = kwargs

    def render(self, context):
        if 'request' not in context:
            return ""
        request = context['request']
        view_name = Variable(self.view_name).resolve(context)
        args = [Variable(arg).resolve(context) for arg in self.args]
        kwargs = {}
        for key, value in self.kwargs.items():
            kwargs[key] = Variable(value).resolve(context)

        url = reverse(view_name, args=args, kwargs=kwargs)
        url = url.replace('%40', '@')
        match = resolve(url)
        view = match.func

        try:
            if callable(view):
                old_path = request.path
                try:
                    request.path = url
                    v = view(request, *args, **kwargs)
                    try:
                        content = v.rendered_content
                    except AttributeError:
                        content = v.content
                    return content
                finally:
                    request.path = old_path
            raise ValueError("%r is not callable" % view)
        except:
            if settings.TEMPLATE_DEBUG:
                raise
        return ""


@register.tag
def render_partial(parser, token):
    """
    Inserts the output of a view, using view name.

      {% render_partial view_name arg[ arg2] k=v [k2=v2...] %}

    IMPORTANT: the calling template must receive a context variable called
    'request' containing the original HttpRequest. This means you should be OK
    with permissions and other session state.

    (Note that every argument will be evaluated against context except for the
    names of any keyword arguments.)
    """

    args = []
    kwargs = {}
    tokens = token.split_contents()
    if len(tokens) < 2:
        raise TemplateSyntaxError(
            '%r tag requires one or more arguments' %
            token.contents.split()[0]
        )
    tag_name = tokens.pop(0)
    view_name = tokens.pop(0)
    for token in tokens:
        equals = token.find("=")
        if equals == -1:
            args.append(token)
        else:
            kwargs[str(token[:equals])] = token[equals+1:]
    return ViewNode(view_name, args, kwargs)
