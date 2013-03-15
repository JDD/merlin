# This file is part of Merlin/Arthur.
# Merlin/Arthur is the Copyright (C)2009,2010 of Elliot Rosemarine.

# Individual portions may be copyright by individual contributors, and
# are included in this collective work with permission of the copyright
# owners.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
 
from jinja2 import contextfilter

from Core.config import Config
from Arthur.jinja import filter

@filter
@contextfilter
def url(context, text):
    if context['user'].url in Config.options("alturls"):
        return text.replace(Config.get("URL", "game"), Config.get("alturls", context['user'].url))
    else:
        return text

@filter
def intel(user):
    return user.has_access("arthur_intel")

@filter
def scans(user):
    return user.has_access("arthur_scans")

@filter
def pc(string):
    return "%s%%"%(string,)

@filter
def percent(value, total):
    fraction = float(value) / total if total else 0
    return "%s%%" % (round(fraction * 100, 1),)

@filter
def and_percent(value, total):
    fraction = float(value) / total if total else 0
    return "%s (%s%%)" % (value, round(fraction * 100, 1),)
