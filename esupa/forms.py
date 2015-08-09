# coding=utf-8
#
# Copyright 2015, Abando.com.br
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
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _t, ugettext as _tt

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
        label=_t('Nome completo'),
        help_text=_t('Conforme documentação legal.'))
    document = forms.CharField(
        label=_t('Registro geral (RG)'),
        help_text=_t('Informe número e órgão expeditor. '
                     'Caso não tenha RG, coloque o número de outro documento, como CNH ou Passaporte.'))
    badge = forms.CharField(
        label=_t('Crachá'),
        help_text=_t('O nome que será impresso no seu crachá (badge).'))
    email = forms.EmailField(
        label=_t('E-mail'),
        help_text=_t('Para contato até o dia do Abando.'))
    phone = forms.CharField(
        label=_t('Telefone celular'),
        help_text=_t('Em caso de desencontro no dia do Abando, vamos telefonar esse número.'))
    born = forms.DateField(
        label=_t('Data de nascimento'),
        input_formats='%d/%m/%Y %d/%m/%y'.split(),
        help_text=_t('Informe no formato DD/MM/AAAA.'))
    shirt_size = forms.ChoiceField(
        label=_t('Tamanho da camiseta'),
        choices=tuple(map(lambda a: (a, a), 'P M G GG GGG'.split())))
    blood = forms.CharField(
        label=_t('Tipo sanguíneo'),
        required=False,
        max_length=3,
        help_text=_t('Apenas se souber, informe tipo e fator Rh, por exemplo, O+, AB−, etc.'))
    health_insured = forms.BooleanField(
        label=_t('Possui plano de saúde particular?'),
        required=False)
    contact = forms.CharField(
        label=_t('Contato para emergências'),
        widget=widgets.Textarea,
        help_text=_t('Informe nome, relação, e número de telefone (com DDD).'))
    medication = forms.CharField(
        label=_t('Informações médicas rotineiras e de emergência'),
        required=False,
        widget=widgets.Textarea,
        help_text=_t('Medicação sendo tomada, medicação para crises, pressão alta, diabetes, '
                     'problemas respiratórios, do coração, alergias (alimentares e medicamentosas), '
                     'qualquer problema ou condição que necessite de cuidado especial.'))
    optionals = ModelPricedOptInField(label=_t('Opcional'), required=False)
    agreed = forms.BooleanField(label=_t('Li e concordo com o [regulamento].'))

    class Meta:
        model = Subscription
        exclude = 'event user state wait_until position paid paid_at'.split()

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        subscription = self.instance
        event = subscription.event
        self.fields['optionals'].queryset = event.optional_set
        self._add_agreement_link(event)
        self._add_age_warning(event)
        self.max_born = event.max_born

    def clean_born(self):
        born = self.cleaned_data['born']
        if born > self.max_born:
            raise ValidationError(
                _tt('Somente nascidos até %(date)s.'),
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
        if not event.min_age:
            return
        when = formats.date_format(event.starts_at, 'DATE_FORMAT').lower()
        warning = _tt('Você deverá ter %(age)d anos ou mais no dia %(when)s.') % {'age': event.min_age, 'when': when}
        self.fields['born'].help_text += ' ' + warning


class PartialPayForm(forms.Form):
    amount = forms.DecimalField(
        label=_t('Quantidade a ser paga'),
        help_text=_t('Com o pagamento parcial você pode combinar diferentes formas de pagamento.'))

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
