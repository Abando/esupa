Esupa
=====

Esupa stands for **Event Subscription and Payment**,
and it's meant to handle collection of attendee data and payment
for events that are just big enough for Google Forms and manual deposits being insufficient.

It's created for Abando_, an anual event in Brazil, but we hope this can be universally useful.

.. _Abando: http://www.abando.com.br/

Prerequisites
-------------

- `Python 3`_
- ``pip3 install`` django_ django-pagseguro2_
- ``django-admin crateproject`` *<project-name>*
- ``cd`` *<project-name>*
- ``git clone`` https://bitbucket.org/abando/esupa.git
- Add ``esupa`` to your project's ``INSTALLED_APPS`` and ``urls.py``

.. _Python 3: https://www.python.org/downloads/
.. _django: https://www.djangoproject.com/
.. _django-pagseguro2: https://github.com/allisson/django-pagseguro2/

Contribution guidelines
-----------------------

- Just submit one of the readmap features as a pull request.
- Roadmap:
    - Add support for PayPal_, then maybe some others like Payza_, BCash_, Moip_.
    - Split edit and view mode templates in the subscription view.
    - Have each Event have its own staff list, deal with permissions based on that.

.. _PayPal: https://www.paypal.com/
.. _Payza: https://www.payza.com/
.. _BCash: https://www.bcash.com.br/
.. _Moip: https://moip.com.br/

Authors
-------

At the moment it's all by @ekevoo,
but heavily based on plenty of discussions and advice from @whiteraccoon,
who really helped mature the ideas while working hard at the PHP predecessor of this.
