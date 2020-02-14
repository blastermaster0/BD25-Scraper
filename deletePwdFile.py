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
import sys

# Exit codes used by NZBGet
COMMAND_SUCCESS=93
COMMAND_ERROR=94

host = environ.get("NZBOP_CONTROLIP")
port = environ.get("NZBOP_CONTROLPORT")
username = environ.get("NZBOP_CONTROLUSERNAME")
password = environ.get("NZBOP_CONTROLPASSWORD")
passFile = environ.get("NZBOP_UNPACKPASSFILE")

rpcUrl = 'http://%s:%s@%s:%s/xmlrpc' % (username, password, host, port)

server = ServerProxy(rpcUrl)
listgroups = server.listgroups()

if not listgroups:
    remove(passFile)
sys.exit(COMMAND_SUCCESS)
