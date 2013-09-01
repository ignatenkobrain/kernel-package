#!/usr/bin/env python

# Copyright 2013 Igor Gnatenko
# Author(s): Igor Gnatenko <i.gnatenko.brain AT gmail DOT com>
#            Bjorn Esser <bjoern.esser AT gmail DOT com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
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
  name = "kernel"
  sha = repo.head.commit.hexsha
  prefix = "%s-%s" % (name, sha)
  format = "tar.gz"
  archive = "%s.%s" % (prefix, format)
  directory = "sources"
  ver = [None, None, None, None, None]
  released = False
#  version = ver[0]
#  patchlevel = ver[1]
#  sublevel = ver[2]
#  extraversion = ver[3]
  configs = ["config-debug", "config-generic", "config-i686-PAE", \
             "config-nodebug", "config-x86-32-generic", \
             "config-x86-generic", "config-x86_64-generic"]

class Parser(argparse.ArgumentParser):
  def error(self, message):
    sys.stderr.write("error: %s\n" % message)
    self.print_help()
    sys.exit(2)

def set_args(parser):
  parser.add_argument("--with-patches", dest="patches", action="store_true", \
                      help="enable patches from sources/ directory")

def archive(options):
  os.makedirs(options.directory)
  f = open("%s/%s" % (options.directory, options.archive), "w")
  repo.archive(f, prefix=options.prefix, format=options.format)
  f.close()

def download_file(file_name):
  try:
    os.makedirs("sources")
  except OSError:
    pass
  pg = urlgrabber.progress.TextMeter()
  urlgrabber.urlgrab("http://pkgs.fedoraproject.org/cgit/kernel.git/plain/%s" % file_name, \
                     "sources/%s" % file_name, progress_obj=pg)

def download_configs(options):
  for config in options.configs:
    download_file(config)

def download_spec(options):
  download_file("%s.spec" % options.name)

def download_sources(options):
  download_configs(options)
  download_spec(options)

def parse_spec(options):
  lines = []
  regexp_comment = re.compile(r"^[ ]*#")
  regexp_sources = re.compile(r"^Source[1-9][0-9]+:")
  regexp_newline = re.compile(r"^\n")
  with open("%s/%s.spec" % (options.directory, options.name), "r") as f:
    lines = f.readlines()
  f = open("%s/%s.spec" % (options.directory, options.name), "w")
  for line in lines:
    if re.search ("^%changelog", line):
      break
    if regexp_comment.search(line) is None and \
       regexp_sources.search(line) is None and \
       regexp_newline.search(line) is None:
      if re.search ("^Source0: ", line):
        line = re.sub(r" .*$", " %s" % options.archive, line)
      if re.search("%global released_kernel [01]", line):
        line = re.sub(r"[01]$", "1" if options.released else "0", line)
      f.write(line)
  f.close()

def get_kernel_info(options):
  lines = []
  with open("Makefile", "r") as f:
    lines = [f.next() for x in xrange(5)]
  i = 0
  for line in lines:
    options.ver[i] = re.sub(r"^.* = (.*)\n$", r"\1", line)
    i += 1
  if "=" in options.ver[3]:
    options.ver[3] = None
    options.released = True
  else:
    options.released = False

def main():
  parser = Parser(description="Make RPM from upstream linux kernel easy")
#  set_args(parser)
  args = parser.parse_args()
  options = Options()
  get_kernel_info(options)
  if options.released:
    print "Version: %s.%s.%s" % (options.ver[0], options.ver[1], options.ver[2])
  else:
    print "Version: %s.%s.%s%s" % (options.ver[0], options.ver[1], options.ver[2], options.ver[3])
  print "Codename: %s" % options.ver[4]
  download_sources(options)
  parse_spec(options)
#  Enable after write make rpm
#  archive(options)
  sys.exit(0)

if __name__ == "__main__":
  main()
