# coding=utf-8
from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.utils import formats
from django.utils.html import escape


class SubscriptionForm(forms.Form):
    full_name = forms.CharField(
        label='Nome completo',
        help_text='Conforme documentação legal.')
    document = forms.CharField(
        label='Registro geral (RG)',
        help_text='Informe número e órgão expeditor. Caso não tenha RG, coloque o número de outro documento, como CNH ou Passaporte.')
    badge = forms.CharField(
        label='Crachá',
        help_text='O nome que será impresso no seu crachá (badge).')
    email = forms.EmailField(
        label='E-mail',
        help_text='Para contato até o dia do Abando.')
    phone = forms.CharField(
        label='Telefone celular',
        help_text='Em caso de desencontro no dia do Abando, vamos telefonar esse número.')
    born = forms.DateField(
        label='Data de nascimento',
        input_formats='%Y-%m-%d %m/%d/%Y %m/%d/%y'.split(),
        help_text='Informe no formato DD/MM/AAAA.')
    shirt_size = forms.ChoiceField(
        label='Tamanho da camiseta',
        choices=tuple(map(lambda a: (a, a), 'P M G GG GGG'.split())))
    blood = forms.CharField(
        label='Tipo sanguíneo',
        required=False,
        max_length=3,
        help_text='Apenas se souber, informe tipo e fator Rh, por exemplo, O+, AB−, etc.')
    health_insured = forms.BooleanField(
        label='Possui plano de saúde particular?')
    contact = forms.CharField(
        label='Contato para emergências',
        widget=widgets.Textarea,
        help_text='Informe nome, relação, e número de telefone (com DDD).')
    medication = forms.CharField(
        label='Informações médicas rotineiras e de emergência',
        required=False,
        widget=widgets.Textarea,
        help_text='Medicação sendo tomada, medicação para crises, pressão alta, diabetes, problemas respiratórios, do coração, alergias (alimentares e medicamentosas), qualquer problema ou condição que necessite de cuidado especial.')
    optionals = forms.ModelMultipleChoiceField(
        label='',
        required=False,
        queryset=None,
        widget=widgets.CheckboxSelectMultiple)
    agreed = forms.BooleanField(
        label='Concordo em seguir o código de conduta.')

    def __init__(self, subscription, *args, **kwargs):
        event = subscription.event
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['optionals'].queryset = event.optional_set
        self._add_age_warning(subscription.event)
        self.max_born = event.max_born

    def clean_born(self):
        born = self.cleaned_data['born']
        if born > self.max_born:
            raise ValidationError(
                'Somente nascidos antes de %(date)s.',
                code='too_young',
                params={'date': self.max_born},
            )
        return born

    def freeze(self):
        for field in self.fields.values():
            field.widget = DisplayWidget()
            field.help_text = None

    def _add_age_warning(self, event):
        if not event.min_age:
            return
        when = formats.date_format(event.starts_at, 'DATE_FORMAT').lower()
        warning = ' Você deverá ter %d anos ou mais no dia %s.' % (event.min_age, when)
        self.fields['born'].help_text += warning

    def copy_into(self, subscription):
        # TODO: replace with a smarter loop using self.fields
        cd = self.cleaned_data
        subscription.full_name      = cd['full_name']
        subscription.document       = cd['document']
        subscription.badge          = cd['badge']
        subscription.email          = cd['email']
        subscription.phone          = cd['phone']
        subscription.born           = cd['born']
        subscription.shirt_size     = cd['shirt_size']
        subscription.blood          = cd['blood']
        subscription.health_insured = cd['health_insured']
        subscription.contact        = cd['contact']
        subscription.medication     = cd['medication']
        # subscription.optionals    = cd['optionals'] # FIXME
        subscription.agreed         = cd['agreed']


class DisplayWidget(widgets.Widget):
    def render(self, name, value, attrs=None):
        if value:
            return escape(value).replace('\n', '<br>')
        else:
            return '-'


class UploadForm(forms.Form):
    upload = forms.FileField(label='Comprovante')
    def __init__(self, subscription, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        fmt = 'Deposite R$ %s na conta abaixo e envie foto ou scan do comprovante.\n%s'
        msg = fmt % (subscription.price, subscription.event.deposit_info)
        self.fields['upload'].help_text = msg.replace('\n', '\n<br/>')
