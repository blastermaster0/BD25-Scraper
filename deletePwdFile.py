#!/usr/bin/python

###########################################
### NZBGET POST-PROCESSING SCRIPT       ###

# Delete password file.
#
# This script deletes the password file after all downloads have completed.

### NZBGET POST-PROCESSING SCRIPT       ###
###########################################

from os import environ, remove
from xmlrpclib import ServerProxy


host = environ["NZBOP_CONTROLIP"]
port = environ["NZBOP_CONTROLPORT"]
username = environ["NZBOP_CONTROLUSERNAME"]
password = environ["NZBOP_CONTROLPASSWORD"]
passFile = environ["NZBOP_UNPACKPASSFILE"]

rpcUrl = 'http://%s:%s@%s:%s/xmlrpc' % (username, password, host, port);

server = ServerProxy(rpcUrl)
listgroups = server.listgroups()

if not listgroups:
    remove(passFile)
