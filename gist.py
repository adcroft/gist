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

  parser_listGists = subparsers.add_parser('list',
       help='Lists your gists.',
       description="""Lists all your gists, or those of the specified user (-u option).
                      If you provide your own user id with the -u option, you will see
                      only your public gists.""")
  parser_listGists.add_argument('-u', '--user', type=str, help="A GitHub user's handle.")
  parser_listGists.add_argument('-n', '--nentries', type=int, default=100,
       help='Stop after n gists. Default is 100.')
  parser_listGists.set_defaults(action=listGists)

  parser_gistInfo = subparsers.add_parser('info',
       help='Dumps the meta-information about a gist.',
       description="""Dumps the meta-information about a gist.""")
  parser_gistInfo.add_argument('GISTID', type=str, help="A gist id. Usually a 20 character hex or a long integer.")
  parser_gistInfo.set_defaults(action=gistInfo)

  parser_getGist = subparsers.add_parser('get',
       help='Downloads files from a gist.',
       description="""Downloads files from a gist.""")
  parser_getGist.add_argument('GISTID', type=str, help="A gist id. Usually a 20 character hex or a long integer.")
  parser_getGist.add_argument('-o', '--override', action='store_true', help="Allows local files to be overwritten.")
  parser_getGist.set_defaults(action=getGist)

  parser_createGist = subparsers.add_parser('create',
       help='Creates a gist from a file or files.',
       description="""Creates a gist from a file or files.""")
  parser_createGist.add_argument('FILE', type=str, nargs='+', help="Names of file(s) to upload to gist.")
  parser_createGist.add_argument('-t', '--title', type=str,
       help="Description of gist. By default the file name(s) will be used for the description.")
  parser_createGist.add_argument('-p', '--public', action='store_true',
       help="Creates a public gist. By default a new gist will be private.")
  parser_createGist.set_defaults(action=createGist)

  args = parser.parse_args()

  msg = args.action(args)
  # The actions associated with each sub-command can return a message (errors) or None.
  if msg is not None: print msg


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


def listGists(args):
  """
  Lists gists.
  """

  if args.user is None:
    user, token = getStoredToken()
    if token is None:
      return "No stored token found. Use '" + _thisTool + " login <USER>' to obtain a token."
    authHeader = {'Authorization': 'token '+token}
    url = _APIurl + '/gists'
  else:
    user = args.user
    authHeader = {}
    url = _APIurl + '/users/' + user + '/gists'
  entries = 0
  while url is not None:
    response = requests.get(url, headers=authHeader, stream=True)
    if response.status_code != 200:
      return 'ERROR: '+json.loads(response.text).get('message',
             'No message returned from server.')
    url = response.links['next']['url'] if 'next' in response.links else None
    for g in response.json():
      if (entries>=args.nentries):
        return 'Stopped streaming after %i responses.' % entries
      visibility = 'public' if g['public'] else 'private'
      print '%-20s %-7s %s' % (g['id'], visibility, g['description'])
      entries += 1


def gistInfo(args):
  """
  Shows all meta-information about a particular gist.
  """

  user, token = getStoredToken()
  if token is None:
    authHeader = {}
    print "No stored token found. Trying with public access. Otherwise use '" + \
          _thisTool + " login <USER>' to obtain a token."
  else: authHeader = {'Authorization': 'token '+token}
  url = _APIurl + '/gists/' + args.GISTID
  response = requests.get(url, headers=authHeader)
  if response.status_code != 200:
    return 'ERROR: '+json.loads(response.text).get('message',
           'No message returned from server.')
  d = response.json()
  # Remove some of the more verbose data for clarity
  del d['owner']
  del d['user']
  for f in d['files']:
    del d['files'][f]['content']
  del d['history']
  print json.dumps(d, indent=2)


def getGist(args):
  """
  Downloads files in gist.
  """

  user, token = getStoredToken()
  if token is None:
    authHeader = {}
    print "No stored token found. Trying with public access. Otherwise use '" + \
          _thisTool + " login <USER>' to obtain a token."
  else: authHeader = {'Authorization': 'token '+token}
  url = _APIurl + '/gists/' + args.GISTID
  response = requests.get(url, headers=authHeader)
  if response.status_code != 200:
    return 'ERROR: '+json.loads(response.text).get('message',
           'No message returned from server.')
  d = response.json()
  for f in d['files']:
    fo = d['files'][f]
    filename = fo['filename']
    if os.path.isfile(filename) and not args.override:
      return "'" + filename + "' already exists. Use the -o option to override. Stopping."
    if fo['truncated']: # TODO
      return "'" + filename + "' is truncated. This feature is not yet implemented!"
    else:
      with open(filename,'w') as fh:
        fh.write(fo['content'])
        print 'Downloaded',filename


def createGist(args):
  """
  Create gist from files
  """

  files = {}
  for f in args.FILE:
    with open(f,'r') as fh: files[f] = {'content': fh.read()}
  title = ' '.join(args.FILE) if args.title is None else args.title
  payload = {'description': title,
             'public': args.public,
             'files': files}
  user, token = getStoredToken()
  if token is None:
    return "No stored token found. Use '" + _thisTool + " login <USER>' to obtain a token."
  authHeader = {'Authorization': 'token '+token}
  response = requests.post(_APIurl + '/gists',
                           headers=authHeader,
                           data=json.dumps(payload))
  if response.status_code != 201:
    return 'ERROR: '+json.loads(response.text).get('message',
           'No message returned from server.')
  return 'Created gist with id '+response.json()['id']

# Invoke the top-level procedure
if __name__ == '__main__': main()
