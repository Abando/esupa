Esupa
=====

Esupa is a free software `licensed under the Apache License`_
meant to handle collection of attendee data and payment
for events that are just big enough for Google Forms and manual deposits being insufficient.

It's created for Abando_, an annual event in Brazil, but I hope this can be universally useful.

The name stands for **Event Subscription and Payment**.

.. _licensed under the Apache License: LICENSE.rst
.. _Abando: http://www.abando.com.br/


Installation
------------

- `Python 3`_
- ``pip3 install`` django_ django-pagseguro2_
- ``django-admin crateproject`` *<project-name>*
- ``cd`` *<project-name>*
- ``git clone`` https://bitbucket.org/abando/esupa.git
- Add ``esupa`` to your project's ``INSTALLED_APPS`` and ``urls.py``
- ``manage.py compilemessages`` (optional; only needed for localization)

.. _Python 3: https://www.python.org/downloads/
.. _django: https://www.djangoproject.com/
.. _django-pagseguro2: https://github.com/allisson/django-pagseguro2/


Usage
-----

You must set up a registration and authenticiation application.
Just ``django.contrib.auth`` does the job, but I use python3-oneall_.

Then use the Django Administration panel to create a new Event. Make sure to set its date in the future.

After this is set, you can navigate to the main page and you will see the main subscription page.

.. _python3-oneall: https://github/ekevoo/python3-oneall


Contribution guidelines
-----------------------

- Just submit one of the roadmap features as a pull request.

  - Follow PEP-8_ and PEP-20_ and you're golden.
  - Eventually I'll also abide to PEP-257_ too, in which case so must pull requests.

- Roadmap:

  - Have each Event have its own staff list, deal with permissions based on that. Some with read permissions only.

- These would be nice too, but aren't pressing issues for now.

  - Add support more payment processors. Payza_? BCash_?, Moip_?
  - Localization of optionals and other database-stored strings.
  - Flesh out partial payments. How should new expiry dates be calculated?

.. _PEP-8: https://www.python.org/dev/peps/pep-0008/
.. _PEP-20: https://www.python.org/dev/peps/pep-0020/
.. _PEP-257: https://www.python.org/dev/peps/pep-0257/
.. _Payza: https://www.payza.com/
.. _BCash: https://www.bcash.com.br/
.. _Moip: https://moip.com.br/


Authors
-------

At the moment it's all by Ekevoo,
but heavily based on plenty of discussions and advice from WhiteRaccoon,
who really helped mature the ideas while working hard at the PHP predecessor of this.
