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
import subprocess
import stat

WORK_DIR = os.path.dirname(sys.argv[0])
repo = git.Repo(WORK_DIR)
assert repo.bare == False
repo.config_reader()

class Options():
  name = "kernel"
  sha = repo.head.commit.hexsha
  prefix = None
  format = "tar.gz"
  archive = "%s-%s.%s" % (name, sha, format)
  patch = None
  directory = "sources"
  ver = [None, None, None, None, None]
  released = False
  sources = ["config-arm64", "config-arm-generic", "config-armv7", "config-armv7-generic", \
             "config-armv7-lpae", "config-debug", "config-generic", "config-i686-PAE", \
             "config-nodebug", "config-powerpc32-generic", "config-powerpc32-smp", \
             "config-powerpc64", "config-powerpc64p7", "config-powerpc-generic", "config-s390x", \
             "config-x86-32-generic", "config-x86_64-generic", "config-x86-generic", \
             "cpupower.config", "cpupower.service", "Makefile", "Makefile.config", "Makefile.release", \
             "merge.pl", "mod-extra.list", "mod-extra.sh", "mod-sign.sh", "x509.genkey"]
  try:
    with open("%s/config-local" % directory, "r"):
      pass
  except IOError:
    sources.append("config-local")
  execute = ["merge.pl", "mod-extra.sh", "mod-sign.sh"]

class Parser(argparse.ArgumentParser):
  def error(self, message):
    sys.stderr.write("error: %s\n" % message)
    self.print_help()
    sys.exit(2)

def set_args(parser):
  parser.add_argument("--with-patches", dest="patches", action="store_true", \
                      help="enable patches from sources/ directory")

def archive(options):
  f = open("%s/%s" % (options.directory, options.archive), "w")
  repo.archive(f, prefix=options.prefix, format=options.format)
  f.close()

def download_file(file_name):
  pg = urlgrabber.progress.TextMeter()
  urlgrabber.urlgrab("http://pkgs.fedoraproject.org/cgit/kernel.git/plain/%s" % file_name, \
                     "sources/%s" % file_name, progress_obj=pg)

def download_sources(options):
  for source in options.sources:
    download_file(source)

def download_spec(options):
  download_file("%s.spec" % options.name)

def set_execute(options):
  for source in options.execute:
    src = "%s/%s" % (options.directory, source)
    st = os.stat(src)
    os.chmod(src, st.st_mode | stat.S_IEXEC)

def download_files(options):
  try:
    os.makedirs(options.directory)
  except OSError:
    pass
  download_sources(options)
  download_spec(options)
  set_execute(options)

def parse_spec(options):
  lines = []
  with open("%s/%s.spec" % (options.directory, options.name), "r") as f:
    lines = f.readlines()
  i = 0
  while i < len(lines):
    if re.search("^%changelog", lines[i]):
      try:
        while True:
          del lines[i]
      except IndexError:
        pass
    elif re.search("^%global released_kernel [01]", lines[i]):
      lines[i] = re.sub(r"[01]", "1" if options.released else "0", lines[i])
      i += 1
    elif re.search("^%define base_sublevel [0-9]+", lines[i]):
      lines[i] = re.sub(r"[0-9]+", options.ver[1] if options.released else (str(int(options.ver[1]) - 1)), lines[i])
      i += 1
    elif re.search("^%define stable_update [0-9]+", lines[i]):
      lines[i] = re.sub(r"[0-9]+", options.ver[2], lines[i])
      i += 1
    elif re.search("^%define rcrev [0-9]+", lines[i]):
      lines[i] = re.sub(r"[0-9]+", re.sub(r"[^0-9]", "", options.ver[3]) if not options.released else "0", lines[i])
      i += 1
    elif re.search("^%define gitrev [0-9]+", lines[i]):
      lines[i] = re.sub(r"[0-9]+", "0", lines[i])
      i += 1
    elif re.search("^%define debugbuildsenabled [01]", lines[i]):
      lines[i] = re.sub(r"[01]", "0", lines[i])
      i += 1
    elif re.search("^%define rawhide_skip_docs [01]", lines[i]):
      lines[i] = re.sub(r"[01]", "1", lines[i])
      i += 1
    elif re.search("^%define with_vanilla ", lines[i]):
      lines[i] = re.sub(r"[01]}(.*) [01]", r"0}\1 1", lines[i])
      i += 1
    elif re.search("^Source0: ", lines[i]):
      lines[i] = re.sub(r" .*$", " %s" % options.archive, lines[i])
      i += 1
    elif re.search("^(Patch[0-9]+:|Apply(Optional|)Patch) ", lines[i]) and \
         re.search("^Patch00: patch-3.%{upstream_sublevel}-rc%{rcrev}.xz", lines[i]) is None:
      lines[i] = re.sub(r"^", "#", lines[i])
      i += 1
    else:
      i += 1
  f = open("%s/%s.spec" % (options.directory, options.name), "w")
  for line in lines:
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

def make_patch(options):
  options.patchfile = "%s/patch-%s.%s%s" % (options.directory, options.ver[0], options.ver[1], options.ver[3])
  patch = open(options.patchfile, "w")
  p = subprocess.Popen("git diff %s v%s.%s" % (options.sha, options.ver[0], \
                                               (int(options.ver[1]) - 1)), shell=True, universal_newlines=True, stdout=patch)
  p.wait()
  patch.flush()
  patch.close()
  try:
    os.remove("%s.xz" % options.patchfile)
  except OSError:
    pass
  subprocess.call(["xz", "-z", options.patchfile])

def main():
  parser = Parser(description="Make RPM from upstream linux kernel easy")
#  set_args(parser)
  args = parser.parse_args()
  options = Options()
  get_kernel_info(options)
  options.prefix = "linux-%s.%s/" % (options.ver[0], options.ver[1] if options.released else (int(options.ver[1]) - 1))
  if options.released:
    print "Version: %s.%s.%s" % (options.ver[0], options.ver[1], options.ver[2])
  else:
    print "Version: %s.%s.%s%s" % (options.ver[0], options.ver[1], options.ver[2], options.ver[3])
  print "Codename: %s" % options.ver[4]
  download_files(options)
  if not options.released:
    make_patch(options)
  parse_spec(options)
  archive(options)
  sys.exit(0)

if __name__ == "__main__":
  main()
