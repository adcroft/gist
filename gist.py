#!/usr/bin/env python

import argparse
import getpass
import json
import os.path
import requests
import socket
import sys, stat

_thisTool = 'gist.py'
_tokenFile = os.path.expanduser('~/.gist_token')
_APIurl = 'https://api.github.com'

def main():
  """
  Parse arguments and act accordingly.
  """

  parser = argparse.ArgumentParser(
    description=_thisTool+' is a command-line tool for uploading and listing gists.',
    epilog='Written by A.Adcroft, 2014 (https://github.com/Adcroft).')

  parser.add_argument('-d', '--debug', action='store_true', help='Turn on debugging.')
  subparsers = parser.add_subparsers()

  # These area sub-commands
  parser_logIn = subparsers.add_parser('login',
       help='Logs on to GitHub and obtains an application token.',
       description="""Logs on to GitHub and obtains an application token. See
                      https://github.com/settings/applications for a list of your
                      personal access tokens where you can revoke a token if needed.
                      The token is stored in file '"""+_tokenFile+"'.")
  parser_logIn.add_argument('USER', type=str, help='Your GitHub handle.')
  parser_logIn.set_defaults(action=logIn)

  parser_logOut = subparsers.add_parser('logout',
       help='Delete and forget authorized application token.',
       description="""Delete and forget the authorized application token. The
                      token is deleted from your authorized applications on GitHub and
                      the local token store file '"""+_tokenFile+"""' is also deleted.
                      See https://github.com/settings/applications for a list of your
                      personal access tokens where you can revoke a token if needed.""")
  parser_logOut.set_defaults(action=logOut)

  args = parser.parse_args()
  print args.action(args)

  return



  response = requests.get(_APIurl+'/users/Adcroft/gists', auth=('Adcroft',password))
  content = json.loads(response.text)
  #print json.dumps(content, indent=2)
  for g in content:
    print g['git_pull_url'],g['description']
  payload = {'note': 'CLI helper'}
  response = requests.post(_APIurl+'/authorizations', auth=('Adcroft',password),
                           data=json.dumps(payload))
  content = json.loads(response.text)
  print json.dumps(content, indent=2)


def logIn(args):
  """
  Request a token from GitHub
  """

  _, token = getStoredToken()
  if token is not None:
    return "A GitHub token already exists. Use '" + _thisTool + \
          " logout' to delete the token before creating a new token.'"

  password = getpass.getpass('GitHub password: ')
  payload = {'note': _thisTool+' CLI helper, first authenticated from '
                     + socket.gethostname() + ' ('
                     + socket.gethostbyname(socket.gethostname()) + ')',
             'scopes': ['gist']}
  response = requests.post(_APIurl + '/authorizations',
                           auth=(args.USER,password),
                           data=json.dumps(payload))
  if response.status_code >= 400:
    return 'ERROR: '+json.loads(response.text).get('message',
             'No message returned from server.')
  content = json.loads(response.text)
  storeToken( args.USER, content['token'] )
  return 'Log in successful'


def getStoredToken():
  """
  Reads the token from _tokenFile or returns None is file is absent.
  """
  try:
    with open(_tokenFile,'r') as f:
      j = json.load(f)
      return j['user'], j['token']
  except: return None, None


def storeToken(user, token):
  """
  Writes token to _tokenFile.
  """
  with open(_tokenFile,'w') as f:
    os.chmod(_tokenFile, stat.S_IREAD|stat.S_IWRITE)
    json.dump({'user':user, 'token':token}, f)


def logOut(args):
  """
  Deletes token from GitHub and _tokenFile
  """

  user, token = getStoredToken()
  if token is None:
    return 'No stored token found. Did you already log out?'
  print 'To delete the token on GitHub you must use basic authorization. Leave blank to abort.'
  password = getpass.getpass('GitHub password: ')
  if password is '': return 'Aborting logout'
  response = requests.get(_APIurl + '/authorizations',
                          auth=(user,password))
  if response.status_code != 200:
    return 'ERROR: '+json.loads(response.text).get('message',
             'No message returned from server.')
  content = json.loads(response.text)

  for auth in content:
    i,t = auth['id'], auth['token']
    if t == token: 
      response = requests.delete(_APIurl + '/authorizations/%i'%i,
                                 auth=(user,password))
      if response.status_code != 204:
        return 'ERROR: '+json.loads(response.text).get('message',
             'Was expecting code 204 but got none.')
      os.remove(_tokenFile)
      return 'Log out succesful'
  return 'No matching token found on GitHub. Delete the token on GitHub by hand and remove '+_tokenFile



# Invoke the top-level procedure
if __name__ == '__main__': main()
