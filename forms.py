from django import forms

class SubscriptionForm(forms.Form):
	full_name = forms.CharField(
		label = 'Nome completo',
		help_text = 'Conforme documentação legal.')
	document = forms.CharField(
		label = 'Registro geral (RG)',
		help_text = 'Informe número e órgão expeditor. Caso não tenha RG, coloque o número de outro documento, como CNH ou Passaporte.')
	badge = forms.CharField(
		label = 'Crachá',
		help_text = 'O nome que será impresso no seu crachá (badge).')
	email = forms.EmailField(
		label = 'E-mail',
		help_text = 'Para contato até o dia do Abando.')
	phone = forms.CharField(
		label = 'Telefone celular',
		help_text = 'Em caso de desencontro no dia do Abando, vamos telefonar esse número.')
	born = forms.DateField(
		label = 'Data de nascimento',
		input_formats = '%Y-%m-%d %m/%d/%Y %m/%d/%y'.split(),
		#Você deverá ter {{ event.min_age }} anos ou mais no dia {{ event.starts_at|date:'DATE_FORMAT'|lower }}. Caso tenha dúvidas, <a href='http://abando.com.br/contato/' target='contatoAbando'>entre em contato com a equipe</a>.
		help_text = 'Informe no formato DD/MM/AAAA.')
	shirt_size = forms.ChoiceField(
		label = 'Tamanho da camiseta',
		choices = tuple(map(lambda a:(a,a), 'P M G GG GGG'.split())))
	blood = forms.CharField(
		label = 'Tipo sanguíneo',
		required = False,
		max_length = 3,
		help_text = 'Apenas se souber, informe tipo e fator Rh, por exemplo, O+, AB−, etc.')
	health_insured = forms.BooleanField(
		label = 'Possui plano de saúde particular?')
	contact = forms.CharField(
		label = 'Contato para emergências',
		widget = forms.Textarea,
		help_text = 'Informe nome, relação, e número de telefone (com DDD).')
	medication = forms.CharField(
		label = 'Informações médicas rotineiras e de emergência',
		required = False,
		widget = forms.Textarea,
		help_text = 'Medicação sendo tomada, medicação para crises, pressão alta, diabetes, problemas respiratórios, do coração, alergias (alimentares e medicamentosas), qualquer problema ou condição que necessite de cuidado especial.')
	optionals = forms.ModelMultipleChoiceField(
		queryset = None,
		widget = forms.CheckboxSelectMultiple)
	agreed = forms.BooleanField(
		label = 'Concordo em seguir o código de conduta.')
	def __init__(self, subscription, *args, **kwargs):
		forms.Form.__init__(self, *args, **kwargs)
		self.fields['optionals'].queryset = subscription.event.optional_set
