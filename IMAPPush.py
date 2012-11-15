#!/usr/bin/python

"""
Released under the MIT/X11 License

Copyright (c) 2010 -- Chris Kirkham

 Permission is hereby granted, free of charge, to any person
 obtaining a copy of this software and associated documentation
 files (the "Software"), to deal in the Software without
 restriction, including without limitation the rights to use,
 copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following
 conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
"""

import threading, imaplib2, os, sys, getpass
import re, socket
from Core.string import CRLF
from Core.config import Config
from Core.robocop import push
from time import sleep

ServerTimeout = 29 # Mins (leave if you're not sure)

DEBUG = False # debugMsg() prints the parameter passed if DEBUG is True


"""
The worker class for the thread. Letting a thread wait for the server to send something allows the
main thread (if that's what you call it??) to be used for other stuff -- waiting for UI, for example.
"""
class Idler(threading.Thread):
        
    imap = imaplib2.IMAP4_SSL("imap.gmail.com") # can be changed to another server if needed
    
    stopWaitingEvent = threading.Event()
    #Now, this stopWaitingEvent thing -- it really does make the whole thing work. Basically, 
    #it holds a boolean value which is set and cleared using, oddly enough, the methods set() and
    #clear(). But, the good thing about it is that it has another method, wait(), which holds 
    #execution until it has been set(). I cannot thank threading.Event() enough, I really couldn't
    #have done it without you!
    
    knownAboutMail = [] # will be a list of IDs of messages in the inbox
    killNow = False # stops execution of thread to allow propper closing of conns.
    
    
    """
    Initialise (sorry, I'm from the UK) everything to get ready for PUSHed mail.
    """
    def __init__(self, GMailUsername, GMailPassword):
        
        os.system('clear')
        debugMsg('DEBUG is ENABLED')
        debugMsg('__init__() entered')
                
        try:
            #establish connection to IMAP Server
            self.imap.LOGIN(GMailUsername, GMailPassword)
            self.imap.SELECT("INBOX")
            
            #get the IDs of all messages in the inbox and put in knowAboutMail
            typ, data = self.imap.SEARCH(None, 'ALL')
            self.knownAboutMail = data[0].split()
            
            #now run the inherited __init__ method to create thread
            threading.Thread.__init__(self)
            
        except: #Uh Oh, something went wrong
            print 'ERROR: IMAP Issue. It could be one (or more) of the following:'
            print '- The impalib2.py file needs to be in the same directory as this file'
            print '- You\'re not connected to the internet'
            print '- Google\'s mail server(s) is/are down'
            print '- Your username and/or password is incorrect'
            sys.exit(1)
            
        debugMsg('__init__() exited')
        
        
    """
    The method invoked when the thread id start()ed. Enter a loop executing waitForServer()
    untill kill()ed. waitForServer() can, and should, be continuously executed to be alerted
    of new mail.
    """
    def run(self):
        debugMsg('run() entered')    
        
        #loop until killNow is set by kill() method
        while not self.killNow:
            self.waitForServer()    
            
        debugMsg('run() exited')
            
    
    """
    Relay email contents to merlin via robocop.
    """
    def robonotify(self, header, body):
        # Check for correct "From" address?
        uname = re.findall("(.+)@.+", header['To'])[0].split()[1]
        tick = re.findall("events in tick (\d+)", body)[0]
        newfleets = re.findall("We have detected an open jumpgate from (.+), located at (\d{1,2}):(\d{1,2}):(\d{1,2}). " +\
                               "The fleet will approach our system in tick (\d+) and appears to have (\d+) visible ships.", body)
        recalls = re.findall("The (.+) fleet from (\d{1,2}):(\d{1,2}):(\d{1,2}) has been recalled.", body)
        cons = len(re.findall("Our construction team reports that .+ has been finished", body))
        res = len(re.findall("Our scientists report that .+ has been finished", body))

        # Wrap it up in a bow
        lines = []
        for line in newfleets:
            push("defcall", etype="new", uname=uname, tick=tick, name=line[0], x=line[1], y=line[2], z=line[3], eta=line[4], size=line[5])
        for line in recalls:
            push("defcall", etype="rec", uname=uname, tick=tick, name=line[0], x=line[1], y=line[2], z=line[3])
        if res + cons > 0:
            push("defcall", etype="fin", uname=uname, tick=tick, res=(1 if res else 0))

        
    """
    Name says it all really: get (just) the specified header fields from the server for the 
    specified message ID.
    """
    def getMessageHeaderFieldsById(self, id, fields_tuple):
        debugMsg('getMessageHeaderFieldsById() entered')
        
        #get the entire header
        typ, header = self.imap.FETCH(id, '(RFC822.HEADER)')
        
        #get individual lines
        headerlines = header[0][1].splitlines()
        
        #get the lines that start with the values in fields_tuple
        results = {}
        for field in fields_tuple:
            results[field] = ''
            for line in headerlines:
                if line.startswith(field):
                    results[field] = line
                    
        debugMsg('getMessageHeaderFieldsById() exited')
        return results #which is a dictionary containing the the requested fields
        
        
    """
    The main def for displaying messages. It draws on getMessageHeaderFieldsById() and growlnotify()
    to do so.
    """
    def showNewMailMessages(self):
        debugMsg('showNewMailMessages() entered')
        
        #get IDs of all UNSEEN messages 
        typ, data = self.imap.SEARCH(None, 'UNSEEN')
        
        debugMsg('data - new mail IDs:')
        debugMsg(data, 0)
        
        for id in data[0].split():
            if not id in self.knownAboutMail:
                
                #get From and Subject fields from header
                headerFields = self.getMessageHeaderFieldsById(id, ('From', 'To', 'Subject'))
                print self.imap.fetch(id, '(BODY[TEXT])')[1][0][1]
                
                debugMsg('headerFields dict. (from showNewMailMessage()):')
                debugMsg(headerFields, 0)
                
                #notify
                self.robonotify(headerFields, self.imap.fetch(id, '(BODY[TEXT])')[1][0][1])
                
                #add this message to the list of known messages
                self.knownAboutMail.append(id)
                
        debugMsg('showNewMailMessages() exited')


    """
    Called to stop the script. It stops the continuous while loop in run() and therefore
    stops the thread's execution.
    """
    def kill(self):
        self.killNow = True # to stop while loop in run()
        self.timeout = True # keeps waitForServer() nice
        self.stopWaitingEvent.set() # to let wait() to return and let execution continue


    """
    This is the block of code called by the run() method of the therad. It is what does all 
    the waiting for new mail (well, and timeouts).
    """
    def waitForServer(self):
        debugMsg('waitForServer() entered')
        
        #init
        self.newMail = False
        self.timeout = False
        self.IDLEArgs = ''
        self.stopWaitingEvent.clear()
        
        def _IDLECallback(args):
            self.IDLEArgs = args
            self.stopWaitingEvent.set()
            #_IDLECallack() is entered when the IMAP server responds to the IDLE command when new
            #mail is received. The self.stopWaitingEvent.set() allows the .wait() to return and
            #therefore the rest of waitForServer().
            
            
        #attach callback function, and let server know it should tell us when new mail arrives    
        self.imap.idle(timeout=60*ServerTimeout, callback=_IDLECallback)

        #execution will stay here until either:
        # - a new message is received; or
        # - the timeout has happened 
        #       - we set the timout -- the RFC says the server has the right to forget about 
        #            us after 30 mins of inactivity (i.e. not communicating with server for 30 mins). 
        #            By sending the IDLE command every 29 mins, we won't be forgotten.
        # - Alternatively, the kill() method has been invoked.
        self.stopWaitingEvent.wait()
        
        #self.IDLEArgs has now been filled (if not kill()ed)
        
        if not self.killNow: # skips a chunk of code to sys.exit() more quickly.
            
            if self.IDLEArgs[0][1][0] == ('IDLE terminated (Success)'):
            # This (above) is sent when either: there has been a timeout (server sends); or, there
            # is new mail. We have to check manually to see if there is new mail. 
                
                typ, data = self.imap.SEARCH(None, 'UNSEEN') # like before, get UNSEEN message IDs
                
                debugMsg('Data: ')
                debugMsg(data, 0)
                
                #see if each ID is new, and, if it is, make newMail True
                for id in data[0].split():
                    if not id in self.knownAboutMail:
                        self.newMail = self.newMail or True
                    else:
                        self.timeout = True 
                        # gets executed if there are UNSEEN messages that we have been notified of, 
                        # but we haven't yet read. In this case, it response was just a timeout.
                        
                if data[0] == '': # no IDs, so it was a timeout (but no notified but UNSEEN mail)
                    self.timeout = True
        
            #now there has either been a timeout or a new message -- Do something...
            if self.newMail:
                debugMsg('INFO: New Mail Received')
                self.showNewMailMessages()
                            
            elif self.timeout:
                debugMsg('INFO: A Timeout Occurred')
            
        debugMsg('waitForServer() exited')
            
            

"""
Simple procedure to output debug messages nicely.
"""
def debugMsg(msg, newline=1):
    global DEBUG
    if DEBUG:
        if newline:
            print ' '
        print msg
    
    
"""
Main bit of code to get the ball rolling. It starts the thread and waits for 'q' to be input.
That's it. Nice and simple.
"""
def main():
    IMAPUsername = Config.get("imap", "user")
    IMAPPassword = Config.get("imap", "pass")
    if IMAPPassword == "":
        IMAPPassword = getpass.getpass()
    idler = Idler(IMAPUsername, IMAPPassword)
    idler.start()
    
    print '* Waiting for mail...'
    q = ''
    while not q == 'q':
        q = raw_input('Type \'q\' followed by [ENTER] to quit: ')
        
    idler.kill()    
    idler.imap.CLOSE()
    idler.imap.LOGOUT()
    sys.exit()



if __name__ == '__main__': # then this script is being run on its own, i.e. not imported
    main()
else:
    print 'I don\'t think you meant to import this'
    sys.exit(1)
    
