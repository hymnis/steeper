#!/usr/bin/env python3

from distutils.core import setup
from DistUtilsExtra.command import *

#DEST="/opt/extras.ubuntu.com/steeper/"
DEST="share/steeper/"

class my_build_i18n(build_i18n.build_i18n):
    def run(self):
        build_i18n.build_i18n.run(self)

        df = self.distribution.data_files

        self.distribution.data_files = [(d.replace("share/locale/", DEST+"locale/"), s) for d, s in df]

setup(
      cmdclass = {"build": build_extra.build_extra,
                  "build_i18n": my_build_i18n},
      name = "steeper",
      version = "0.2.1",
      description = "Simple tea steeping timer (mainly for Unity)",
      author = "Peter Dahlman",
      author_email = "peter.dahlman@gmail.com",
      url = "https://github.com/hymnis/steeper",
      license = "GNU GPL v3",
      data_files = [("share/applications/", ["steeper.desktop"]),
                    (DEST+"icons/", ["icons/steeper-scalable.svg",
                    "icons/steeper-48x48.png",
                    "icons/steeper-64x64.png",
                    "icons/steeper-128x128.png"]),
                    (DEST, ["window.ui", "steeper.py", "pycanberra.py", "help.txt"])])
