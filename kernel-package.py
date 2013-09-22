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
import glob
import shutil

WORK_DIR = os.getcwd()

"""
repo.config_reader()
url = repo.remotes.origin.url
valid_url = ["git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git", \
             "http://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git", \
             "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git", \
             "https://github.com/torvalds/linux", \
             "git@github.com:torvalds/linux.git"]
n = 0
while n < len(valid_url):
  if not "%s" % valid_url[n] in url:
    n += 1
  else:
    n = -1
    break
if n != -1:
  print "Wtf? It's not Linus git tree!"
  sys.exit(1)
"""

class Options:
  def __init__(self, work_dir):
    try:
      self.repo = git.Repo(work_dir)
    except git.exc.InvalidGitRepositoryError:
      print "Wtf? This folder not contains valid git repository!"
      sys.exit(1)
    assert self.repo.bare == False
    self.name = "kernel"
    self.hcommit = self.repo.head.commit
    self.sha = self.hcommit.hexsha
    self.prefix = None
    self.format = "tar.gz"
    self.patch = None
    self.directory = "sources"
    self.ver = [None, None, None, None, None]
    self.released = False
    self.get_kernel_info()
    self.prefix = "linux-%s.%s" % (self.ver[0], self.ver[1] if self.released else (int(self.ver[1]) - 1))
    self.sources = ["config-arm64", "config-arm-generic", "config-armv7", "config-armv7-generic", \
                    "config-armv7-lpae", "config-debug", "config-generic", "config-i686-PAE", \
                    "config-nodebug", "config-powerpc32-generic", "config-powerpc32-smp", \
                    "config-powerpc64", "config-powerpc64p7", "config-powerpc-generic", "config-s390x", \
                    "config-x86-32-generic", "config-x86_64-generic", "config-x86-generic", \
                    "cpupower.config", "cpupower.service", "Makefile", "Makefile.config", "Makefile.release", \
                    "merge.pl", "mod-extra.list", "mod-extra.sh", "mod-sign.sh", "x509.genkey"]
    try:
      with open("%s/config-local" % self.directory, "r"):
        pass
    except IOError, e:
      if e.errno == 2:
        self.sources.append("config-local")
    self.execute = ["merge.pl", "mod-extra.sh", "mod-sign.sh"]

  def get_kernel_info(self):
    lines = []
    with open("Makefile", "r") as f:
      lines = [f.next() for x in xrange(5)]
    i = 0
    for line in lines:
      self.ver[i] = re.sub(r"^.* = (.*)\n$", r"\1", line)
      i += 1
    if "=" in self.ver[3]:
      self.ver[3] = None
      self.released = True
    else:
      self.released = False

  def print_info(self):
    if self.released:
      print "Version: %s.%s.%s" % (self.ver[0], self.ver[1], self.ver[2])
    else:
      print "Version: %s.%s.%s%s" % (self.ver[0], self.ver[1], self.ver[2], self.ver[3])
    print "Codename: %s" % self.ver[4]

  def archive(self):
    if not self.released:
      self.repo.git.checkout("v%s.%s" % (self.ver[0], (int(self.ver[1]) - 1)))
    f = open("%s/%s.%s" % (self.directory, self.prefix, self.format), "w")
    self.repo.archive(f, prefix="%s/" % self.prefix, format=self.format)
    f.close()
    if not self.released:
      self.repo.git.checkout(self.sha)

class Parser(argparse.ArgumentParser):
  def error(self, message):
    sys.stderr.write("error: %s\n" % message)
    self.print_help()
    sys.exit(2)

def set_args(parser):
  parser.add_argument("--buildid", dest="buildid", action="store", \
                      help="user build-id")
  parser.add_argument("--check-configs", dest="chk_config", action="store_true", \
                      help="enable check for new CONFIG options")
  parser.add_argument("--separate-debug", dest="separate_debug", action="store_true", \
                      help="separate debug kernel and main kernel")
  parser.add_argument("--without-patches", dest="patches", action="store_false", \
                      help="build kernel w/o/ patches")

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
  download_sources(options)
  download_spec(options)
  set_execute(options)

def parse_spec(options, args):
  lines = []
  with open("%s/%s.spec" % (options.directory, options.name), "r") as f:
    lines = f.readlines()
  first = True
  patches = glob.glob("%s/*.patch" % options.directory)
  patches.sort()
  i = 0
  while i < len(patches):
    patches[i] = re.sub("%s/" % options.directory, "", patches[i])
    i += 1
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
    elif re.search("^# % define buildid .local", lines[i]) and args.buildid:
      lines[i] = re.sub("# % ", "%", lines[i])
      lines[i] = re.sub("local", "%s" % args.buildid, lines[i])
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
    elif re.search("^%global baserelease [0-9]+", lines[i]):
      lines[i] = re.sub(r"[0-9]+", "999" if options.released else "1", lines[i])
      i += 1
    elif re.search("^%define debugbuildsenabled [01]", lines[i]):
      lines[i] = re.sub(r"[01]", "1" if args.separate_debug else "0", lines[i])
      i += 1
    elif re.search("^%define rawhide_skip_docs [01]", lines[i]):
      lines[i] = re.sub(r"[01]", "1", lines[i])
      i += 1
    elif re.search("^%define with_vanilla ", lines[i]):
      lines[i] = re.sub(r"[01]}(.*) [01]", r"1}\1 0", lines[i])
      i += 1
    elif re.search("^%define with_debuginfo ", lines[i]):
      lines[i] = re.sub(r"[01]}(.*) [01]", r"1}\1 0", lines[i])
      i += 1
    elif re.search("^%define with_perf ", lines[i]):
      lines[i] = re.sub(r"[01]}(.*) [01]", r"1}\1 0", lines[i])
      i += 1
    elif re.search("^%define listnewconfig_fail [01]", lines[i]) and not args.chk_config:
      lines[i] = re.sub(r"[01]", "0", lines[i])
      i += 1
    elif re.search("^Source0: ", lines[i]):
      lines[i] = re.sub(r" .*$", " %s.%s" % (options.prefix, options.format), lines[i])
      i += 1
    elif re.search("^%if !%{nopatches}", lines[i]) and args.patches:
      i += 1
      if first:
        j = 100
        for patch in patches:
          lines.insert(i, "Patch%s: %s\n" % (str(j), patch))
          j += 1
          i += 1
        first = False
      else:
        for patch in patches:
          lines.insert(i, "ApplyPatch %s\n" % patch)
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

def make_patch(options):
  if not options.released:
    options.patchfile = "%s/patch-%s.%s%s" % (options.directory, options.ver[0], options.ver[1], options.ver[3])
    patch = open(options.patchfile, "w")
    p = subprocess.Popen("git diff v%s.%s %s" % (options.ver[0], (int(options.ver[1]) - 1), \
                                                 options.sha), shell=True, universal_newlines=True, stdout=patch)
    p.wait()
    patch.flush()
    patch.close()
    subprocess.call(["xz", "-z", options.patchfile])

def make_srpm(options):
  subprocess.call(["rpmbuild", "-bs", "%s/%s.spec" % (options.directory, options.name), \
                   "-D", "_specdir %s/" % options.directory, \
                   "-D", "_sourcedir %s/" % options.directory, \
                   "-D", "_srcrpmdir %s/" % options.directory])

def clean_tree(options, first_clean):
  try:
    os.stat(options.directory)
    if not os.access(options.directory, os.W_OK):
      print "Wtf? I don't have access to \"%s/\" directory!" % options.directory
      sys.exit(1)
  except OSError, e:
    if e.errno == 2:
      os.makedirs(options.directory)
  clean = glob.glob("%s/*" % options.directory)
  i = 0
  while i < len(clean):
    if re.search(".patch$", clean[i]) or \
       re.search("config-local$", clean[i]):
      del clean[i]
    elif re.search(".src.rpm$", clean[i]) and \
         not first_clean:
      del clean[i]
    else:
      i += 1
  for to_clean in clean:
    try:
      os.remove(to_clean)
    except OSError, e:
      if e.errno == 21 or e.errno == 39:
        shutil.rmtree(to_clean)

def main():
  parser = Parser(description="Make RPM from upstream linux kernel easy.")
  set_args(parser)
  args = parser.parse_args()
  options = Options(WORK_DIR)
  options.print_info()
  clean_tree(options, True)
  download_files(options)
  make_patch(options)
  parse_spec(options, args)
  options.archive()
  make_srpm(options)
  clean_tree(options, False)
  sys.exit(0)

if __name__ == "__main__":
  main()
