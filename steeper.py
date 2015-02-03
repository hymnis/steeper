#!/usr/bin/env python3

import time
import json
import locale
import subprocess

# Not for production
#import os
#import pprint

from gi.repository import Unity, GObject, Gtk, Notify, Gdk, Pango, GLib
# from gi.repository import GObject, Gtk, Notify, Gdk, Pango, GLib

GETTEXT_DOMAIN = "steeper"

# Should use libcanberra, but no python bindings so far..
SOUND_ALERT_FILE = "/usr/share/sounds/freedesktop/stereo/complete.oga"

REMIND_DELTA_SECONDS=30

#DATA = os.path.expanduser("~/Dropbox/Src/steeper-workdir/steeper-v2/") # dev/debug path
DATA = "/usr/share/steeper/"

# Use locale instead of gettext, so GTK gets the change
locale.bindtextdomain(GETTEXT_DOMAIN, DATA+"locale/")
locale.textdomain(GETTEXT_DOMAIN)
_ = locale.gettext

class Notification(Notify.Notification):
    def __init__(self):
        image = Gtk.Image()
        image.set_from_file(DATA+"icons/steeper-128x128.png")
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
            body = _("finished %s seconds ago") % time.strftime("%S", time.localtime(elapsed))
        else:
            body = _("finished %s minutes ago") % time.strftime("%M:%S", time.localtime(elapsed))

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
            self.actual_duraction = self.obj["duration"] + (self.obj["increment"] * self.obj["brew"])
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

        transl = (("name", _("Name")), ("duration", _("Duration")), ("increment", _("Brew Increment")), ("brew", _("Brews")), ("brew_toggle", _("Count Brews?")))

        for key, title in transl:
            cell = None
            col = Gtk.TreeViewColumn(title, cell)
            col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

            if key == "brew":
                cell = Gtk.CellRendererText()
                cell.set_property("editable", False)
                cell.set_property("ellipsize", Pango.EllipsizeMode.END)

                col.set_min_width(50)
                col.set_fixed_width(70)
            elif key == "brew_toggle":
                cell = Gtk.CellRendererToggle()
                cell.set_property("activatable", True)
                cell.set_property("radio", False)
                cell.connect("toggled", self._toggled_cb, key)

                col.set_min_width(110)
                col.set_fixed_width(200)
            else:
                cell = Gtk.CellRendererText()
                cell.set_property("ellipsize", Pango.EllipsizeMode.END)
                cell.set_property("editable", True)
                cell.connect("edited", self._edited_cb, key)

                col.set_min_width(120)
                col.set_fixed_width(200)

            col.pack_end(cell, False)
            self._cells.append(cell)

            col.set_cell_data_func(cell, self._data_func, key)
            self._obj.append_column(col)

    def add_addline(self):
        self._model.append({"name": _("New Entry"), "duration": 0, "increment": 30, "brew": "-", "brew_toggle": False})

    def in_edit(self):
        return any([c.get_property("editing") for c in self._cells])

    def _toggled_cb(self, cell, itr, key):
        status = cell.get_active()
        status = False if status else True

        if not status:
            # Disable brew
            self._model[itr]["brew"] = "-"
        elif status:
            # Enable brew
            self._model[itr]["brew"] = 0

        self._model[itr][key] = status

    def _edited_cb(self, cell, itr, value, key):
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

            if t is None: return

            value = t.tm_sec + 60 * t.tm_min + 60*60 * t.tm_hour
        else:
            value = value#.decode("utf-8") # for consistency, obsolete in python3??

        self._model[itr][key] = value

        last = int(itr) == (len(self._model._obj) - 1)

        if last:
            self.add_addline()

    def _data_func(self, col, cell, model, itr, key):
        try:
            v = model[itr][0][key]
        except KeyError as e:
            print("[error] KeyError - missing '"+ key +"' in data list (from file)")
            v = False

        if key == "duration" or key == "increment":
            if v >= 60*60:
                v = time.strftime("%H:%M:%S", time.gmtime(v))
            else:
                v = time.strftime("%M:%S", time.gmtime(v))
        elif key == "brew":
            v = str(v)

        last = int(str(model.get_path(itr))) == (len(model) - 1)

        if key == "brew_toggle":
            cell.set_property("active", v)
        else:
            cell.set_property("style", Pango.Style.ITALIC if last else Pango.Style.NORMAL)
            cell.set_property("text", v)

class ListStore:
    FILE = GLib.get_user_data_dir() + "/steeper.js"

    def __init__(self, obj):
        self._obj = obj

        self.load()

    def load(self):
        try:
            f = open(self.FILE)

            for t in json.load(f):
                self.append(t)
        except:
            pass
        else:
            f.close()

    def save(self):
        f = open(self.FILE, "w")

        json.dump([t[0] for t in self._obj][0:-1], f)

        f.close()

    def __getitem__(self, k):
        return self._obj[k][0]

    def __setitem__(self, k, v):
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

        xml.connect_signals({"hide-widget": lambda w, *args: w.hide_on_delete()})
        about = xml.get_object("aboutdialog1")
        xml.get_object("menuitem_about").connect("activate", lambda *args: about.show())

        self.le = Unity.LauncherEntry.get_for_desktop_file("steeper.desktop")

        self.label = xml.get_object("label1")

        self.start_button = xml.get_object("button1")
        self.start_button.connect("clicked", self.on_button_click)

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

        self.start_button.set_sensitive(not (self.sel == len(self.store._obj) - 1))

    def on_button_click(self, *a):
        if self.timer is None:
            try:
                self.start()
            except ValueError: # gets thrown by timer if duration == 0
                pass
        else:
            self.stop()

    def set_label_text(self):
        name = self.timer.obj["name"]

        t = time.gmtime(self.timer.end - time.time())
        f = "%H:%M:%S" if t.tm_hour > 0 else "%M:%S"

        remaining = time.strftime(f, t)
        self.label.set_text(_("%s: %s remaining") % (name, remaining))

    def start(self):
        self.timer = Timer(self.store[self.sel])
        self.timer.start()
        self.tick_src = GObject.timeout_add_seconds(1, self.do_tick)

        self.le.set_property("progress_visible", True)
        self.le.set_property("progress", 0)

        self.start_button.set_label(_("Stop Timer"))
        self.list._obj.set_sensitive(False)

        self.set_label_text()

        self.window.iconify() # does not minimize atm
        #self.window.hide() # hard to unhide again...

    def stop(self):
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
            # Use libcanberra if possible
            subprocess.Popen(["paplay", SOUND_ALERT_FILE])
#            print('Showing notice, not seen yet...')
#        else:
#            print('Seen before notice is shown?')

        return not self.seen

    def start_notification_loop(self):
        self.seen = False
        self.show_notification()
        self.notify_src = GObject.timeout_add_seconds(REMIND_DELTA_SECONDS, self.show_notification)
#        print('Notification loop started ('+ str(self.notify_src) +')')

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
        self.stop()
        self.store.save()
        self.main.quit()

    def timer_noticed(self, *a):
        if self.timer and not self.timer.running:
#            print("Timer has been seen!")
            self.seen = True
            self.stop()
        else:
#            print("Timer has not been seen...")

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
        item = self.store._obj.get_value(itr,0)

        if not item["brew_toggle"]:
            return False

        if modifier == "+":
            newValue = item["brew"] + value
        elif modifier == "-":
            newValue = item["brew"] - value
        else:
            newValue = value

        item["brew"] = newValue

        current = self.list._obj.get_cursor()
        self.list._obj.set_cursor(current[0]) # trigger treeview update (focus row)

if __name__ == "__main__":
    c = Controller()
    c.run()
