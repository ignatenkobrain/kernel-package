#!/usr/bin/env python

# Copyright 2013 Igor Gnatenko
# Author(s): Igor Gnatenko <i.gnatenko.brain AT gmail DOT com>
#            Bjorn Esser <bjoern.esser AT gmail DOT com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; version 2 of the License.
# See http://www.gnu.org/copyleft/gpl.html for the full text of the license.

import os
import sys
import ConfigParser
import argparse
import urllib
import git
import re
import sh

WORK_DIR = os.path.dirname(sys.argv[0])
repo = git.Repo(WORK_DIR)
assert repo.bare == False
repo.config_reader()

class Options():
  name = 'kernel'
  sha = repo.head.commit.hexsha
  prefix = '%s-%s' % (name, sha)
  format = 'tar.gz'
  archive = '%s.%s' % (prefix, format)
  version = None
  patch = None

def out(line):
  sys.stdout.write(line)

def err(line):
  sys.stderr.write(line)

class Parser(argparse.ArgumentParser):
  def error(self, message):
    sys.stderr.write('error: %s\n' % message)
    self.print_help()
    sys.exit(2)

def set_args(parser):
  parser.add_argument('--with-patches', action='store_true', help='start bisecting')
  parser.add_argument('--with-patch', action='store', metavar='/path/to/patch', help='reset bisecting')
  parser.add_argument('--arch', action='store', help='arch')

def archive(options):
  f = open(options.archive, 'w')
  repo.archive(f, prefix=options.prefix, format=options.format)
  f.close()

def print_commit():
  print "HEAD commit: %s\n" % sha

"""
def bisect(args):
  state = None
  commit = ''
  if args.start:
    state = 'start'
  elif args.reset:
    state = 'reset'
  elif args.skip:
    state = 'skip'
    commit = args.skip
  elif args.good:
    state = 'good'
    commit = args.good
  elif args.bad:
    state = 'bad'
    commit = args.bad
  elif args.log:
    state = 'log'
  else:
    err('Nothing to do. Use -h for help.' + '\n')
    sys.exit(1)

  try:
    sh.git.bisect(state, commit, _out=out, _err=err)
  except:
    pass
"""

def download_file(file_name):
  os.makedirs('files')
  urllib.urlretrieve('http://pkgs.fedoraproject.org/cgit/kernel.git/plain/%s' % file_name, 'files/%s' % file_name)

#def make_config()
  

def get_kernel_info(options):
  flag_ver = False
  flag_patch = False
  with open('Makefile', 'r') as f:
    for line in f:
      if 'VERSION' in line:
        if not flag_ver:
          version = line.split(" ")
          options.version = re.sub('\n', '', version[2])
          flag_ver = True
        else:
          continue
      if 'PATCHLEVEL' in line:
        if not flag_patch:
          patch = line.split(" ")
          options.patch = re.sub('\n', '', patch[2])
          flag_patch = True
        else:
          continue

#      line.split
#      options.version = 

def make_rpm():
  os.makedirs('rpms/%s' % sha)

#def create_spec():
  

def main():
  parser = Parser(description='Make RPM from upstream linux kernel easy')
  set_args(parser)
  options = Options()
#  archive(options)
  get_kernel_info(options)
  print "Version: %s.%s" % (options.version, options.patch)
#  download_file('config-local')
"""
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
"""
#  args = parser.parse_args()

if __name__ == "__main__":
  main()
