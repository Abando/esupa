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
from logging import getLogger

from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.utils import formats
from django.utils.formats import get_format
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy, ugettext

from .models import Subscription, Optional

log = getLogger(__name__)


class ModelPricedOptInField(forms.ModelMultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def __init__(self, **kwargs):
        forms.ModelMultipleChoiceField.__init__(self, None, **kwargs)

    def label_from_instance(self, obj):
        assert isinstance(obj, Optional)
        if obj.price:
            return '%s (R$ %s)' % (obj.name, obj.price)
        else:
            return '%s (grátis)' % obj.name


class SubscriptionForm(forms.ModelForm):
    full_name = forms.CharField(
        label=ugettext_lazy('Full name'),
        help_text=ugettext_lazy('As in legal documentation.'))
    document = forms.CharField(
        label=ugettext_lazy('ID'),
        help_text=ugettext_lazy('Type of document and its number.'))
    badge = forms.CharField(
        label=ugettext_lazy('Badge'),
        help_text=ugettext_lazy('Name to be printed on con badge.'))
    email = forms.EmailField(
        label=ugettext_lazy('E-mail'),
        help_text=ugettext_lazy('For contact before event date.'))
    phone = forms.CharField(
        label=ugettext_lazy('Cell phone'),
        help_text=ugettext_lazy('For contact at event date.'))
    born = forms.DateField(
        label=ugettext_lazy('Birth date'))
    shirt_size = forms.ChoiceField(
        label=ugettext_lazy('Shirt size'),
        choices=tuple(map(lambda a: (a, a), 'P M G GG GGG'.split())))
    blood = forms.CharField(
        label=ugettext_lazy('Blood type'),
        required=False,
        max_length=3,
        help_text=ugettext_lazy("Only if you're sure, blood type and Rh factor, such as O+, AB−, etc."))
    health_insured = forms.BooleanField(
        label=ugettext_lazy('Do you have private health plan coverage in the region?'),
        required=False)
    contact = forms.CharField(
        label=ugettext_lazy('Emergency contact'),
        widget=widgets.Textarea,
        help_text=ugettext_lazy('Nome, relationship, and phone number with area code.'))
    medication = forms.CharField(
        label=ugettext_lazy('Routine and emergency medical information'),
        required=False,
        widget=widgets.Textarea,
        help_text=ugettext_lazy(
            "Routine medication, crisis medication, blood pressure, diabetes, breathing conditions, heart "
            "conditions, food or medication allergies, any sort of condition that requires special care."))
    optionals = ModelPricedOptInField(label=ugettext_lazy('Optional'), required=False)
    agreed = forms.BooleanField(label=ugettext_lazy('Read and agreed to [terms and conditions].'))

    class Meta:
        model = Subscription
        exclude = 'event user state wait_until position paid paid_at'.split()

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        subscription = self.instance
        event = subscription.event
        self.fields['optionals'].queryset = event.optional_set.all()
        self._add_agreement_link(event)
        self._add_age_warning(event)
        self.max_born = event.max_born

    def clean_born(self):
        born = self.cleaned_data['born']
        if born > self.max_born:
            raise ValidationError(
                ugettext('Must be born until %(date)s.'),
                code='too_young',
                params={'date': self.max_born},
            )
        return born

    def _add_agreement_link(self, event):
        label = str(self.fields['agreed'].label)
        url = event.agreement_url
        if url:
            label = mark_safe(label.replace('[', '<a href="%s">' % event.agreement_url).replace(']', '</a>'))
        else:
            label = label.replace('[', '').replace(']', '')
        self.fields['agreed'].label = label

    def _add_age_warning(self, event):
        msg = []
        if event.min_age:
            when = formats.date_format(event.starts_at, 'DATE_FORMAT').lower()
            msg.append(ugettext('You must be %(age)d or older at %(when)s.') % {'age': event.min_age, 'when': when})
        msg.append(ugettext('Write in format:'))
        msg.append(get_format('DATE_INPUT_FORMATS')[0].replace('%', ''))
        self.fields['born'].help_text += ' '.join(msg)


class PartialPayForm(forms.Form):
    amount = forms.DecimalField(
        label=ugettext_lazy('Amount to be paid'),
        help_text=ugettext_lazy('You can pay partially to combine different payment methods.'))

    def __init__(self, amount):
        super().__init__({'amount': amount})


class ManualTransactionForm(forms.Form):
    amount = forms.DecimalField()
    when = forms.DateTimeField(initial=now)
    attachment = forms.FileField(required=False)
    notes = forms.CharField(required=False)

    def __init__(self, subscription):
        if isinstance(subscription, Subscription):
            super().__init__()
            self.fields['amount'].initial = subscription.get_owing
        else:
            super().__init__(subscription)
