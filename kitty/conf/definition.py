#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPL v3 Copyright: 2018, Kovid Goyal <kovid at kovidgoyal.net>

import re
from functools import partial

from .utils import to_bool


def to_string(x):
    return x


class Group:

    __slots__ = 'name', 'short_text', 'start_text', 'end_text'

    def __init__(self, name, short_text, start_text='', end_text=''):
        self.name, self.short_text = name, short_text.strip()
        self.start_text, self.end_text = start_text.strip(), end_text.strip()


class Option:

    __slots__ = 'name', 'group', 'short_text', 'long_text', 'option_type', 'defval_as_string', 'defval', 'add_to_default'

    def __init__(self, name, group, defval, option_type, short_text, long_text, add_to_default):
        self.name, self.group, self.short_text = name, group, short_text
        self.long_text, self.option_type = long_text.strip(), option_type
        self.defval_as_string, self.defval = defval, option_type(defval)
        self.add_to_default = add_to_default


def option(
        all_options,
        group,
        name,
        defval,
        short_text='',
        long_text='',
        option_type=to_string,
        add_to_default=True
):
    is_multiple = name.startswith('+')
    if is_multiple:
        name = name[1:]
    defval_type = type(defval)
    if defval_type is not str:
        if option_type is to_string:
            if defval_type is bool:
                option_type = to_bool
            else:
                option_type = defval_type
        if defval_type is bool:
            defval = 'yes' if defval else 'no'
        else:
            defval = str(defval)

    key = name
    if is_multiple:
        key = name + ' ' + defval.partition(' ')[0]
    ans = Option(name, group[0], defval, option_type, short_text, long_text, add_to_default)
    all_options[key] = ans
    return ans


def option_func(all_options, all_groups):
    all_groups = {k: Group(k, *v) for k, v in all_groups.items()}
    group = [None]

    def change_group(name):
        group[0] = all_groups[name]

    return partial(option, all_options, group), change_group, all_groups


def merged_opts(all_options, opt, i):
    yield opt
    for k in range(i + 1, len(all_options)):
        q = all_options[k]
        if not q.short_text:
            yield q
        else:
            break


def remove_markup(text):
    return re.sub(r':(.+?):`(.+?)`', r'\2', text, flags=re.DOTALL)


def render_block(text):
    text = remove_markup(text)
    lines = text.splitlines()
    return '\n'.join('#: ' + line for line in lines)


def render_group(a, group):
    a('# ' + group.short_text + ' {{''{')
    a('')
    if group.start_text:
        a(render_block(group.start_text))
        a('')


def as_conf_file(all_options):
    ans = ['# vim:fileencoding=utf-8:ft=conf:foldmethod=marker', '']
    a = ans.append
    current_group = None
    all_options = list(all_options)
    for i, opt in enumerate(all_options):
        if not opt.short_text:
            continue
        if opt.group is not current_group:
            if current_group:
                if current_group.end_text:
                    a(''), a(current_group.end_text)
                a('# }}''}'), a('')

            current_group = opt.group
            render_group(a, current_group)
        mopts = list(merged_opts(all_options, opt, i))
        a(render_block(opt.long_text or opt.short_text))
        a('')
        sz = max(len(x.name) for x in mopts)
        for mo in mopts:
            prefix = '' if mo.add_to_default else '# '
            a(('{}{:%ds} {}' % sz).format(prefix, mo.name, mo.defval_as_string))
        a('')
    if current_group:
        if current_group.end_text:
            a(''), a(current_group.end_text)
        a('# }}''}')
    return ans