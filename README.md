[![Build Status](https://travis-ci.org/hymnis/steeper.svg?branch=master)](https://travis-ci.org/hymnis/steeper)

# Steeper

Based on *teatime-unity* by Pavel Rojtberg.

## Name
The name comes partly from the fact that it's a tool for measuring steeping time of tea, but also that the duration curve gets steeper for every brew (using increment and brew counter).

## Features
- Brew counter
- Brew duration increment (based on counter)
- Optional brew counting

## Todo
- [x] libcanberra support (for audio notification, support provided by [pycanberra](https://github.com/psykoyiko/pycanberra/))
- [ ] Settings (custom notification sound, temperature unit etc.)
- [ ] Help (how to delete, reset counter etc. intended use and background)
- [ ] Better menu (setting, help, about, quit)
- [x] Manual brew count adjustment (dec/inc, maybe arrow buttons?)
- [x] Add temperature label (for each entry, only indicating correct temperature)
- [ ] List sorting and/or support for manual order
- [ ] Refactoring, clean-up and such (TreeView init for example)
- [x] Unit testing (basic)
- [ ] Unit testing (extensive)
- [ ] Support for negative increment (some teas you should decrese brew time)

## Ideas / Suggestions
- Mode setting, basic or advanced. Disables/enables extra features like brew counter, temperature display and so on. One simple timer and clean UI in basic and a more precise and adjustable timer and UI in advanced.
- Progress-bar, showing how near completion the current brew is (not very useful, window is usually minimized)

## Building package
If you are running Debian/Ubuntu you can easily build a .deb package for clean installation.  
Just run ```dpkg-buildpackage -b``` in the root directory and a package will be created and placed in the directory above.

## Installation
If you are running Debian/Ubuntu just follow the instructions above and create a package, then run:
```
sudo dpkg -i steeper_<version>.deb
```
It's also possible to copy the files by hand to install location or run the application from a directory of your choosing, but that requires some modification of the code to work properly.
