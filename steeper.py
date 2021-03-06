#!/usr/bin/env python3

import time
import json
import locale
import logging
import os.path
import pycanberra
import sys
import getopt

import gi
gi.require_version('Unity', '7.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Unity, GObject, Gtk, Notify, Gdk, Pango, GLib

GETTEXT_DOMAIN = "steeper"
REMIND_DELTA_SECONDS = 30
DATA = "/usr/share/steeper/"
# DATA = "/home/hymnis/ownCloud/src/steeper-workdir/steeper-git/"

# Use locale instead of gettext, so GTK gets the change
locale.bindtextdomain(GETTEXT_DOMAIN, DATA + "locale/")
locale.textdomain(GETTEXT_DOMAIN)
_ = locale.gettext


class Notification(Notify.Notification):
    def __init__(self):
        image = Gtk.Image()
        image.set_from_file(DATA + "icons/steeper-128x128.png")
        icon_pixbuf = image.get_pixbuf()

        Notify.Notification.__init__(self)
        self.set_urgency(Notify.Urgency.LOW)

        if icon_pixbuf is not None:
            self.set_image_from_pixbuf(icon_pixbuf)

    def set_info(self, timer):
        elapsed = time.time() - timer.end

        if elapsed < 20:
            body = _("finished just now")
        elif elapsed < 60:
            body = _("finished %s seconds ago") % time.strftime(
                "%S", time.localtime(elapsed))
        else:
            body = _("finished %s minutes ago") % time.strftime(
                "%M:%S", time.localtime(elapsed))

        self.update(_("%s is ready") % timer.obj["name"], body, None)


class Timer:
    def __init__(self, obj):
        if obj["duration"] == 0:
            raise ValueError

        self.obj = obj
        self.running = False
        self.begin = None
        self.end = None
        self.actual_duraction = None

    def start(self):
        if self.obj["brew_toggle"]:
            self.actual_duraction = self.obj[
                "duration"] + (self.obj["increment"] * self.obj["brew"])
        else:
            self.actual_duraction = self.obj["duration"]

        self.running = True
        self.begin = time.time()
        self.end = self.begin + self.actual_duraction

    def get_progress(self):
        t = time.time()
        progress = (t - self.begin) / self.actual_duraction

        self.running = progress < 1

        return progress


class TreeView:
    def __init__(self, obj, model):
        self._obj = obj

        self._model = model
        self._cells = []

        temperature_range = Gtk.ListStore(str)

        for i in range(50, 100):
            temperature_range.prepend([str(i) + " °C"])

        transl = (
            ("name", _("Name")),
            ("temperature", _("Temp.")),
            ("duration", _("Duration")),
            ("increment", _("Increment")),
            ("brew", _("Brews")),
            ("brew_toggle", _("Count Brews?")))
        cell_align = [0.0, 0.5]
        col_settings = {"min": 110, "max": 200, "align": 0.0}

        for key, title in transl:
            cell = None
            col = Gtk.TreeViewColumn(title, cell)
            col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

            if key == "brew_toggle":
                cell = Gtk.CellRendererToggle()
                cell.set_property("activatable", True)
                cell.set_property("radio", False)
                cell.connect("toggled", self._toggled_cb, key)

                cell_align = [0.5, 0.5]
                col_settings["align"] = 0.5
                col_settings["min"] = 110
                col_settings["max"] = 200
            elif key == "temperature":
                cell = Gtk.CellRendererCombo()
                cell.set_property("editable", True)
                cell.set_property("model", temperature_range)
                cell.set_property("text-column", 0)
                cell.set_property("has-entry", False)
                cell.connect("edited", self._edited_combo, key)

                cell_align = [0.5, 0.5]
                col_settings["align"] = 0.5
                col_settings["min"] = 65
                col_settings["max"] = 80
            elif key == "brew":
                cell = Gtk.CellRendererSpin()
                cell.set_property("editable", True)
                cell.connect("edited", self._edited_spin, key)

            # value=0, lower=0, upper=0, step_incr=0, page_incr=0, page_size=0
                adjustment = Gtk.Adjustment(0, 0, 50, 1, 10, 0)
                cell.set_property("adjustment", adjustment)

                cell_align = [0.5, 0.5]
                col_settings["align"] = 0.5
                col_settings["min"] = 90
                col_settings["max"] = 100
            else:
                cell = Gtk.CellRendererText()
                cell.set_property("ellipsize", Pango.EllipsizeMode.END)

                cell.set_property("editable", True)
                cell.connect("edited", self._edited_cb, key)

                if key == "name":
                    col_settings["min"] = 120
                    col_settings["max"] = 200
                elif key == "duration":
                    cell_align = [0.5, 0.5]
                    col_settings["align"] = 0.5
                    col_settings["min"] = 80
                    col_settings["max"] = 100
                elif key == "increment":
                    cell_align = [0.5, 0.5]
                    col_settings["align"] = 0.5
                    col_settings["min"] = 90
                    col_settings["max"] = 110

            cell.set_alignment(cell_align[0], cell_align[1])
            col.set_alignment(col_settings["align"])
            col.set_min_width(col_settings["min"])
            col.set_fixed_width(col_settings["max"])
            col.pack_end(cell, False)
            self._cells.append(cell)

            col.set_cell_data_func(cell, self._data_func, key)
            self._obj.append_column(col)

    def add_addline(self):
        self._model.append({
            "name": _("New Entry"),
            "temperature": "70 °C",
            "duration": 0,
            "increment": 30,
            "brew": "-",
            "brew_toggle": False
        })

    def in_edit(self):
        return any([c.get_property("editing") for c in self._cells])

    def _toggled_cb(self, cell, itr, key):
        logging.debug("TreeView: Toggled CB")

        status = cell.get_active()
        status = False if status else True

        if not status:
            # Disable brew
            if key == "brew_toggle":
                self._model[itr]["brew"] = "-"
        elif status:
            # Enable brew
            if key == "brew_toggle":
                self._model[itr]["brew"] = 0

        self._model[itr][key] = status

    def _edited_combo(self, cell, itr, value, key):
        logging.debug("TreeView: Edited COMBO")

        self._model[itr][key] = value

    def _edited_cb(self, cell, itr, value, key):
        logging.debug("TreeView: Edited CB")

        # Allow different input formats
        formats = ["%M", "%M:%S", "%M.%S", "%H:%M:%S"]

        if key == "duration" or key == "increment":
            t = None

            for f in formats:
                try:
                    t = time.strptime(value, f)
                    break
                except:
                    continue

            if t is None:
                return

            value = t.tm_sec + 60 * t.tm_min + 60 * 60 * t.tm_hour
        elif key == "temperature":
            pass
        # else:
            # value = value

        self._model[itr][key] = value

        last = int(itr) == (len(self._model._obj) - 1)

        if last:
            self.add_addline()

    def _edited_spin(self, cell, itr, value, key):
        logging.debug("TreeView: Edited SPIN")

        if key == "brew" and self._model[itr][key] != "-":
            self._model[itr][key] = int(value)

    def _data_func(self, col, cell, model, itr, key):
        try:
            v = model[itr][0][key]
        except KeyError as e:
            print(
                "[error] KeyError - missing '" +
                key + "' in data list (from file)." +
                " (" + e + ")")
            v = False

        if key == "duration" or key == "increment":
            if v >= 60 * 60:
                v = time.strftime("%H:%M:%S", time.gmtime(v))
            else:
                v = time.strftime("%M:%S", time.gmtime(v))
        elif key == "brew":
            v = str(v)

            if v == "-":
                cell.set_property("editable", False)
            else:
                cell.set_property("editable", True)
        elif key == "temperature":
            v = str(v)

        last = int(str(model.get_path(itr))) == (len(model) - 1)

        if key == "brew_toggle":
            cell.set_property("active", v)
        else:
            cell.set_property(
                "style", Pango.Style.ITALIC if last else Pango.Style.NORMAL)
            cell.set_property("text", v)


class ListStore:
    FILE = GLib.get_user_data_dir() + "/steeper/steeper.json"

    def __init__(self, obj):
        self._obj = obj

        self.load()

    def load(self):
        try:
            if not os.path.isdir(os.path.dirname(self.FILE)):
                os.mkdir(os.path.dirname(self.FILE))

            f = open(self.FILE, "r+")

            for t in json.load(f):
                self.append(t)
        except:
            pass
        else:
            f.close()

    def save(self):
        logging.debug("ListStore: Save")

        try:
            f = open(self.FILE, "w")

            json.dump([t[0] for t in self._obj][0:-1], f)
        except IOError as e:
            print("IOError: ", e)
        except:
            pass
        else:
            f.close()

    def __getitem__(self, k):
        logging.debug("ListStore: GetItem")
        return self._obj[k][0]

    def __setitem__(self, k, v):
        logging.debug("ListStore: SetItem")
        self._obj[k][0] = v

    def append(self, v):
        self._obj.append((v,))


class Controller:
    def __init__(self):
        self.seen = None
        self.timer = None
        self.notify_src = None
        self.tick_src = None

        Notify.init("Steeper")

        xml = Gtk.Builder()
        xml.set_translation_domain(GETTEXT_DOMAIN)
        xml.add_from_file(DATA + "window.ui")

        xml.connect_signals({
            "hide-widget": lambda w,
            *args: w.hide_on_delete()})

        # Quit
        xml.get_object("menuitem_quit").connect(
            "activate", lambda *args: self.end())

        # Help
        self.helpWnd = xml.get_object("helpdialog1")
        xml.get_object("menuitem_help").connect(
            "activate", lambda *args: self.show_help())

        # Don't show help item if we are missing the help document
        if os.path.isfile(DATA + "help.txt") is False:
            xml.get_object("menuitem_help").hide()

        # About
        aboutWnd = xml.get_object("aboutdialog1")
        xml.get_object("menuitem_about").connect(
            "activate", lambda *args: aboutWnd.show())

        self.le = Unity.LauncherEntry.get_for_desktop_file("steeper.desktop")

        # Timer label
        self.label = xml.get_object("label1")

        # Start button
        self.start_button = xml.get_object("button1")
        self.start_button.connect("clicked", self.on_button_click)

        # List and data
        self.store = ListStore(xml.get_object("liststore1"))
        self.list = TreeView(xml.get_object("treeview1"), self.store)
        self.list._obj.connect("cursor-changed", self.on_sel_changed)
        self.list.add_addline()

        self.window = xml.get_object("window1")
        self.window.connect("delete-event", self.end)
        self.window.connect("window-state-event", self.timer_noticed)
        self.window.connect("focus-in-event", self.timer_noticed)
        self.window.connect("key-press-event", self.on_key_press)
        self.window.show()

        self.notification = Notification()
        self.main = GObject.MainLoop()

    def on_key_press(self, caller, ev):
        key = Gdk.keyval_name(ev.keyval)

        if key == "Delete" and not self.list.in_edit():
            # Don't allow deletion of addline
            if self.sel == len(self.store._obj) - 1:
                return

            itr = self.store._obj.get_iter(self.sel)
            self.store._obj.remove(itr)
        elif key == "BackSpace" and not self.list.in_edit():
            self.reset_brew_counter()

    def on_sel_changed(self, *a):
        self.sel = self.list._obj.get_cursor()[0]

        if self.sel is None:
            # Happens on delete?
            return

        self.sel = int(str(self.sel))

        self.start_button.set_sensitive(
            not (self.sel == len(self.store._obj) - 1))

    def on_button_click(self, *a):
        '''Start/stop time'''
        if self.timer is None:
            try:
                self.start()
            except ValueError:  # gets thrown by timer if duration == 0
                pass
        else:
            self.stop()

    def show_help(self, *a):
        '''Show help dialog
        Get dialog information from glade file, populate and then display it
        If we actually have a help file to get data from'''
        if os.path.isfile(DATA + "help.txt"):
            xml = Gtk.Builder()
            xml.set_translation_domain(GETTEXT_DOMAIN)
            xml.add_from_file(DATA + "window.ui")

            self.helpWnd = xml.get_object("helpdialog1")
            self.help = xml.get_object("textview1")
            self.help_buffer = self.help.get_buffer()

            # Help close button
            help_close_button = xml.get_object("button2")
            help_close_button.connect(
                "clicked", lambda *args: self.helpWnd.hide())

            help_text = open(DATA + "help.txt", "r")
            h_tag = self.help_buffer.create_tag(
                "h", size_points=16, weight=Pango.Weight.BOLD)
            i_tag = self.help_buffer.create_tag(
                "i", style=Pango.Style.ITALIC)
            b_tag = self.help_buffer.create_tag(
                "b", weight=Pango.Weight.BOLD)

            for line in help_text:
                position = self.help_buffer.get_end_iter()

                if str(line)[:1] == "=":  # Headline
                    line = str(line)[1:]
                    self.help_buffer.insert_with_tags(
                        position, str(line) + "\n", h_tag)
                elif str(line)[:1] == "*":  # Bold first word
                    line = str(line)[1:]
                    parts = line.split(" ", 1)

                    if parts[0] is not None:
                        self.help_buffer.insert_with_tags(
                            position, str(parts[0]), b_tag)
                    if len(parts) == 2:
                        line = parts[1]
                        self.help_buffer.insert(position, str(line) + "\n")
                else:  # Normal
                    self.help_buffer.insert(position, str(line) + "\n")

            self.helpWnd.show()

    def set_label_text(self):
        name = self.timer.obj["name"]

        t = time.gmtime(self.timer.end - time.time())
        f = "%H:%M:%S" if t.tm_hour > 0 else "%M:%S"

        remaining = time.strftime(f, t)
        self.label.set_text(_("%s: %s remaining") % (name, remaining))

    def start(self):
        '''Start timer'''
        self.timer = Timer(self.store[self.sel])
        self.timer.start()
        self.tick_src = GObject.timeout_add_seconds(1, self.do_tick)

        self.le.set_property("progress_visible", True)
        self.le.set_property("progress", 0)

        self.start_button.set_label(_("Stop Timer"))
        self.list._obj.set_sensitive(False)

        self.set_label_text()

        self.window.iconify()

    def stop(self):
        '''Stop timer'''
        self.le.set_property("urgent", False)
        self.le.set_property("progress_visible", False)
        self.start_button.set_label(_("Start Timer"))
        self.list._obj.set_sensitive(True)
        self.timer = None
        self.label.set_text(_("No Running Timers"))

        if self.tick_src is not None:
            GObject.source_remove(self.tick_src)
            self.tick_src = None

        if self.notify_src is not None:
            GObject.source_remove(self.notify_src)
            self.notify_src = None

    def run(self):
        self.main.run()

    def show_notification(self):
        if not self.seen:
            self.notification.set_info(self.timer)
            self.notification.show()
            canberra = pycanberra.Canberra()
            canberra.easy_play_sync("complete")
            canberra.destroy()

        return not self.seen

    def start_notification_loop(self):
        self.seen = False
        self.show_notification()
        self.notify_src = GObject.timeout_add_seconds(
            REMIND_DELTA_SECONDS, self.show_notification)

    def do_tick(self):
        p = self.timer.get_progress()
        self.le.set_property("progress", min(p, 1))

        self.set_label_text()

        if p >= 1:
            if self.timer and not self.timer.running:
                self.increment_brew_counter()

            self.start_notification_loop()
            self.le.set_property("urgent", True)

        # If true, gets called again
        return p < 1.0

    def end(self, *a):
        '''End process
        Stop timer, save data and then quit'''
        self.stop()
        self.store.save()
        self.main.quit()

    def timer_noticed(self, *a):
        if self.timer and not self.timer.running:
            self.seen = True
            self.stop()

    def reset_brew_counter(self):
        self.brew_counter_update(0)

    def increment_brew_counter(self):
        self.brew_counter_update(+1)

    def brew_counter_update(self, value):
        # Check value, will we need a modifier?
        if value < 0:
            modifier = "-"
        elif value > 0:
            modifier = "+"
        else:
            modifier = None

        # Get value from store
        itr = self.store._obj.get_iter(self.sel)
        item = self.store._obj.get_value(itr, 0)

        if not item["brew_toggle"]:
            return False

        if modifier == "+":
            newValue = item["brew"] + value
        elif modifier == "-":
            newValue = item["brew"] - value
        else:
            newValue = value

        # Set new value and update TreeView
        item["brew"] = newValue
        current = self.list._obj.get_cursor()
        self.list._obj.set_cursor(current[0])  # trigger treeview update


def main(argv):
    help_txt = "Options:\n -h, --help\t\t\tShow this help" \
        "\n -l <level>, --log=<level>\tSet log level"
    loglevel = "WARNING"  # default value

    try:
        opts, args = getopt.getopt(argv, "hl:", ["help", "log="])
    except getopt.GetoptError:
        print(help_txt)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(help_txt)
            sys.exit()
        elif opt in ("-l", "--log"):
            loglevel = arg

    try:
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)
    except ValueError as e:
        print(e)
        sys.exit(2)

    logging.basicConfig(level=numeric_level)

    logging.debug("Debug logging is ON")


if __name__ == "__main__":
    main(sys.argv[1:])

    c = Controller()
    c.run()
