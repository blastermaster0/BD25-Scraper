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


host = os.environ["NZBOP_CONTROLIP"]
port = os.environ["NZBOP_CONTROLPORT"]
username = os.environ["NZBOP_CONTROLUSERNAME"]
password = os.environ["NZBOP_CONTROLPASSWORD"]
passFile = os.environ["NZBOP_UNPACKPASSFILE"]

rpcUrl = f"http://{host}:{port}@{username}:{password}/xmlrpc"

server = ServerProxy(rpcUrl)
listgroups = server.listgroups()

if not listgroups:
    remove(passFile)

