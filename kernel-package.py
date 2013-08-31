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
import urlgrabber
import urlgrabber.progress
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
  patchlevel = None
  subversion = None
  extraversion = None
  configs = ['config-debug', 'config-generic', 'config-i686-PAE', \
             'config-nodebug', 'config-x86-32-generic', \
             'config-x86-generic', 'config-x86_64-generic']

class Parser(argparse.ArgumentParser):
  def error(self, message):
    sys.stderr.write('error: %s\n' % message)
    self.print_help()
    sys.exit(2)

def set_args(parser):
  parser.add_argument('--download-configs', dest='dlcfg', action='store_true', help='download latest Fedora kernel configs')
  parser.add_argument('--with-patches', dest='patches', action='store_true', help='start bisecting')
  parser.add_argument('--arch', action='store', help='arch')

def archive(options):
  os.makedirs('sources')
  f = open('sources/%s' % options.archive, 'w')
  repo.archive(f, prefix=options.prefix, format=options.format)
  f.close()

def download_file(file_name):
  try:
    os.makedirs('sources')
  except OSError:
    pass
  pg = urlgrabber.progress.TextMeter()
  urlgrabber.urlgrab('http://pkgs.fedoraproject.org/cgit/kernel.git/plain/%s' % file_name, 'sources/%s' % file_name, progress_obj=pg)

def download_configs(options):
  for config in options.configs:
    download_file(config)

def get_kernel_info(options):
  flag_version = False
  flag_patchlevel = False
  flag_sublevel = False
  flag_extraversion = False
  with open('Makefile', 'r') as f:
    for line in f:
      if 'VERSION' in line:
        if not flag_version:
          version = line.split(" ")
          options.version = re.sub('\n', '', version[2])
          flag_version = True
        else:
          continue
      if 'PATCHLEVEL' in line:
        if not flag_patchlevel:
          patchlevel = line.split(" ")
          options.patchlevel = re.sub('\n', '', patchlevel[2])
          flag_patchlevel = True
        else:
          continue
      if 'SUBLEVEL' in line:
        if not flag_sublevel:
          sublevel = line.split(" ")
          options.sublevel = re.sub('\n', '', sublevel[2])
          flag_sublevel = True
        else:
          continue
      if 'EXTRAVERSION' in line:
        if not flag_extraversion:
          extraversion = line.split(" ")
          options.extraversion = re.sub('\n', '', extraversion[2])
          flag_extraversion = True
        else:
          continue

def make_rpm():
  os.makedirs('rpms/%s' % sha)

#def create_spec():
  

def main():
  parser = Parser(description='Make RPM from upstream linux kernel easy')
  set_args(parser)
  args = parser.parse_args()
  options = Options()
  get_kernel_info(options)
  print "Version: %s.%s.%s%s" % (options.version, options.patchlevel, options.sublevel, options.extraversion)
#  Enable after write make rpm
#  archive(options)
  if args.dlcfg:
    download_configs(options)

if __name__ == "__main__":
  main()
