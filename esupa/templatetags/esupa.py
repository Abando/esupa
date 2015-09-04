# -*- coding: utf-8 -*-
#
# Copyright 2015, Ekevoo.com.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
#
from datetime import datetime

from django.template import Library
from django.template.defaultfilters import date
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince, timeuntil
from django.utils.translation import ugettext

register = Library()


@register.filter(expects_localtime=True)
def relative(when, include_span_tag=True):
    delta = (when - datetime.now(tz=when.tzinfo)).total_seconds()
    if abs(delta) < 10:  # 10 seconds threshold
        text = ugettext(u"just now")
    elif delta < 0:
        text = ugettext(u"%s ago") % timesince(when)
    else:
        text = ugettext(u"in %s") % timeuntil(when)
    if include_span_tag:
        text = mark_safe(u"<span title='%(absolute)s'>%(relative)s</span>"
                         % {'relative': text, 'absolute': date(when, 'r')})
    return text
