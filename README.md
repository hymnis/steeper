# Steeper

Based on *teatime-unity* by Pavel Rojtberg.

## Name
The name comes partly from the fact that it's a tool for measuring steeping time of tea, but also that the duration curve gets steeper for every brew (using increment and brew counter).

## Features
- Brew counter
- Brew duration increment (based on counter)
- Optional brew counting

## Todo
- libcanbarra support (for audio notification)
- Settings (custom notification sound, temperature unit etc.)
- Help (how to delete, reset counter etc. intended use and background)
- Better menu (setting, help, about, quit)
- Manual brew count adjustment (dec/inc, maybe arrow buttons?)
- ~~Add temperature label (for each entry, only indicating correct temperature)~~
- List sorting and/or support for manual order
- Refactoring, clean-up and such (TreeView init for example)
- Unit testing
- Support for negative increment (some teas you should decrese brew time)

## Ideas / Suggestions
- Mode setting, basic or advanced. Disables/enables extra features like brew counter, temperature display and so on. One simple timer and clean UI in basic and a more precise and adjustable timer and UI in advanced.

## Building package
If you are running Debian/Ubuntu you can easily build a .deb package for clean installation.  
Just run ```dpkg-buildpackage -b``` in the root directory and a package will be created and placed in the directory above.

## Installation
If you are running Debian/Ubuntu just follow the instuctions above and create a package, then run: ```sudo dpkg -i steeper_<version>.deb```.  
It's also possible to copy the files by hand to install location or run the application from a directory of your choosing, but that requires some modification of the code to work properly.