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

log = getLogger(__name__)


def load_submodules(app_config):
    from importlib import import_module
    from pkgutil import walk_packages
    from .base import PaymentBase, payment_methods
    from ..models import payment_names

    if payment_methods:
        return
    for path in __path__:
        log.debug('Will traverse %s', path)
    for loader, modname, ispkg in walk_packages(__path__):
        log.info('Found sub%s %s' % ('package' if ispkg else 'module', modname))
        try:
            module = import_module('.'.join((__name__, modname)))
            log.debug('Imported payment module: %s', modname)
            if hasattr(module, 'PaymentMethod'):
                subclass = module.PaymentMethod
                assert issubclass(subclass, PaymentBase)
                payment_methods[subclass.CODE] = subclass
                payment_names[subclass.CODE] = subclass.TITLE
                subclass.static_init(app_config, module)
                log.info('Loaded payment module %s: code=%d, title=%s', modname, subclass.CODE, subclass.TITLE)
            else:
                log.warn('No class PaymentMethod in module: %s', modname)
        except (ImportError, SyntaxError) as e:
            log.warn('Failed to import payment module: %s', modname)
            log.debug(e, exc_info=True)
