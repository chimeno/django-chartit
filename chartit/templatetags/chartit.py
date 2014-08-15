import re
try:
    import simplejson as json
except:
    import json
import datetime

import posixpath

from itertools import izip_longest
from collections import defaultdict

from django import template
from django.utils.safestring import mark_safe
from django.conf import settings
from django.utils.translation import ugettext as _

from ..charts import Chart, PivotChart

try:
    CHARTIT_JS_REL_PATH = settings.CHARTIT_JS_REL_PATH
    if CHARTIT_JS_REL_PATH[0] == '/':
        CHARTIT_JS_REL_PATH = CHARTIT_JS_REL_PATH[1:]
    CHART_LOADER_URL = posixpath.join(settings.STATIC_URL, 
                                      CHARTIT_JS_REL_PATH,
                                      'chartloader.js')
except AttributeError:
    CHARTIT_JS_REL_PATH = 'chartit/js/'
    CHART_LOADER_URL = posixpath.join(settings.STATIC_URL, 
                                      CHARTIT_JS_REL_PATH,
                                      'chartloader.js')

register = template.Library()


class DateTimeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        else:
            return super(DateTimeJSONEncoder, self).default(obj)


def _recursive_translate(item):
    if item and isinstance(item, basestring):
        return _(item)
    if isinstance(item, list):
        return [_recursive_translate(x) for x in item]
    if isinstance(item, dict) or isinstance(item, defaultdict):
        for key, value in item.items():
            item[key] = _recursive_translate(value)
            # Cache our original value for client side reference
            if isinstance(value, basestring):
                item[key + '_raw'] = value
    return item


@register.filter
def load_charts(chart_list=None, render_to=''):
    """Loads the ``Chart``/``PivotChart`` objects in the ``chart_list`` to the 
    HTML elements with id's specified in ``render_to``. 
    
    :Arguments:
    
    - **chart_list** - a list of Chart/PivotChart objects. If there is just a 
      single element, the Chart/PivotChart object can be passed directly 
      instead of a list with a single element.
       
    - **render_to** - a comma separated string of HTML element id's where the 
      charts needs to be rendered to. If the element id of a specific chart 
      is already defined during the chart creation, the ``render_to`` for that 
      specific chart can be an empty string or a space.
      
      For example, ``render_to = 'container1, , container3'`` renders three 
      charts to three locations in the HTML page. The first one will be 
      rendered in the HTML element with id ``container1``, the second 
      one to it's default location that was specified in ``chart_options`` 
      when the Chart/PivotChart object was created, and the third one in the
      element with id ``container3``.
    
    :returns:
     
    - a JSON array of the HighCharts Chart options. Also returns a link
      to the ``chartloader.js`` javascript file to be embedded in the webpage. 
      The ``chartloader.js`` has a jQuery script that renders a HighChart for 
      each of the options in the JSON array"""
    embed_script = (
      '<script type="text/javascript">\n'
      'var _chartit_hco_array = %s;\n</script>\n'
      '<script src="%s" type="text/javascript">\n</script>')
   
    if chart_list is not None:
        if isinstance(chart_list, (Chart, PivotChart)):
            chart_list = [chart_list]
        chart_list = [c.hcoptions for c in chart_list]

        # If translating, wrap series data in translate tags
        if len(settings.LANGUAGES) > 1:
            translated_chart_list = []
            for chart in chart_list:
                if chart.get('translate', True):
                    translated_chart_list.append(
                        _recursive_translate(chart)
                    )
                else:
                    translated_chart_list.append(chart)
            chart_list = translated_chart_list

        render_to_list = [s.strip() for s in render_to.split(',')]
        for hco, render_to in izip_longest(chart_list, render_to_list):
            if render_to:
                hco['chart']['renderTo'] = render_to
        embed_script = (embed_script % (json.dumps(chart_list,
                                                         use_decimal=True,
                                                         cls=DateTimeJSONEncoder),
                                        CHART_LOADER_URL))

        # Escape functions
        embed_script = re.sub('"(?P<fn>function\(\){.+?})"', '\g<fn>', embed_script)
    else:
        embed_script = embed_script %((), CHART_LOADER_URL)
    return mark_safe(embed_script)
