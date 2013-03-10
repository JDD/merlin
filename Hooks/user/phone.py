# This file is part of Merlin.
# Merlin is the Copyright (C)2008,2009,2010 of Robin K. Hansen, Elliot Rosemarine, Andreas Jacobsen.

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
 
from Core.db import session
from Core.maps import User, PhoneFriend
from Core.loadable import loadable, route, require_user

class phone(loadable):
    """Lookup someone's phone number or set permissions for who can view your number if you've not set public (pref)"""
    usage = " <list|allow|deny|show> [pnick]"
    access = 2 # Public
    subcommands = ["phone_list", "phone_show", "phone_override"]
    subaccess = [3, 3, 1]
    
    @route(r"list")
    @require_user
    def list(self, message, user, params):
        # List of users than can see your phonenumber
        message.reply(self.list_reply(user, True))
    
    @route(r"list\s+(\S+)", access = "phone_list")
    def list_other(self, message, user, params):
        member = User.load(name=params.group(1), exact=False)
        if member is None:
            message.alert("%s is not a valid user."%(params.group(1),))
            return
        
        message.reply(self.list_reply(member, user==member))
    
    def list_reply(self, user, isuser):
        friends = user.phonefriends
        if len(friends) < 1:
            reply = "%s no friends. How sad. Maybe %s should go post on http://grouphug.us or something."
            return reply % (("%s has"%(user.name,),user.name,), ("You have","you",),)[isuser]
        reply = "The following people can view %s phone number:"
        for friend in friends:
            reply += " "+friend.name
        return reply % (("%s's"%(user.name,),), ("your",),)[isuser]
    
    @route(r"allow\s+(\S+)")
    @require_user
    def allow(self, message, user, params):
        trustee=params.group(1)
        member = User.load(name=trustee,exact=False)
        if member is None:
            message.alert("%s is not a valid user."%(trustee,))
            return
        
        # Add a PhoneFriend
        if member in user.phonefriends:
            reply="%s can already access your phone number."%(member.name,)
        else:
            user.phonefriends.append(member)
            session.commit()
            reply="Added %s to the list of people able to view your phone number."%(member.name,)
        message.reply(reply)
    
    @route(r"deny\s+(\S+)")
    @require_user
    def deny(self, message, user, params):
        trustee=params.group(1)
        member = User.load(name=trustee,exact=False)
        if member is None:
            message.alert("%s is not a valid user."%(trustee,))
            return
        
        # Remove a PhoneFriend
        friends = user.phonefriends
        if member not in friends:
            reply="Could not find %s among the people allowed to see your phone number." % (member.name,)
        else:
            session.query(PhoneFriend).filter_by(user=user, friend=member).delete(synchronize_session=False)
            session.commit()
            reply="Removed %s from the list of people allowed to see your phone number." % (member.name,)
        message.reply(reply)
    
    @route(r"show\s+(\S+)")
    @require_user
    def show(self, message, user, params):
        trustee=params.group(1)
        member = User.load(name=trustee,exact=False)
        if member is None:
            message.alert("%s is not a valid user."%(trustee,))
            return
        
        # Show a phone number
        # Instead of the no-public-Alki message, message.alert() will always return in private
        if user == member:
            if user.phone:
                reply="Your phone number is %s."%(user.phone,)
            else:
                reply="You haven't set your phone number. To set your phone number, do !pref phone=1-800-HOT-BIRD."
            message.alert(reply)
            return
        
        if user.has_access("phone_override") or member.pubphone and user.has_access("phone_show"):
            message.alert("%s says his phone number is %s"%(member.name,member.phone))
            return
        friends = member.phonefriends
        if user not in friends:
            message.reply("%s won't let you see their phone number. That paranoid cunt just doesn't trust you I guess."%(member.name,))
            return
        if member.phone:
            message.alert("%s says his phone number is %s"%(member.name,member.phone))
        else:
            message.reply("%s hasn't shared his phone number. What a paranoid cunt ."%(member.name,))
            return
