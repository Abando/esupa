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
"""
Pieces of code that do not accomplish any business goal and have no internal dependency.
"""
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirectBase


class FunctionDictionary(dict):
    """ A dictionary that includes decorators to add functions to it as they're declared. """

    def __init__(self, default_function=None, **kwargs):
        """
        The constructor can be used normally or as a decorator. If used as a decorator, it affects the get() method.

        :param default_function: Function to be given by ``get(key)`` if ``key`` is not found.
        """
        self._default = default_function
        super().__init__(**kwargs)

    def register(self, *keys):
        """
        Adds the decorated function to the dictionary. Use it as follows:

        .. code-block::

            my_func_dict = FunctionDictionary()
            @my_func_dict.register('key1', 'key2')
            def my_func_dict(int_arg):
                return int_arg * 2

            my_func_dict['key1'](1) == my_func_dict['key2'](1)
        """

        def x(func) -> FunctionDictionary:
            for key in keys:
                self[key] = func
            return self

        return x

    def get(self, key, default=None):
        return super().get(key, default or self._default)


def named(name: str):
    """ A decorator to add a name to a function. """

    def apply_decoration(func):
        func.name = name
        return func

    return apply_decoration


class HttpResponseSeeOther(HttpResponseRedirectBase):
    status_code = 303


def prg_redirect(destination: str, *args) -> HttpResponseSeeOther:
    """ Post-Redirect-Get """
    if not destination.startswith('http'):
        destination = reverse(destination, args=args)
    return HttpResponseSeeOther(destination)
