# -*- coding: utf-8 -*-
#
#  sessionplugin.py (v0.0.1)
#    ~ imitates notepad++ session save/restore behaviour
#
#  Copyright (C) 2024 - jia3apb

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330,
#  Boston, MA 02111-1307, USA.


import gi
gi.require_version('Xed', '1.0')
from gi.repository import GObject, Xed, Gio, GtkSource, Gtk
import os
import json
import hashlib
from pprint import pprint


class SessionPlugin(GObject.Object, Xed.WindowActivatable):
    __gtype_name__ = "SessionPlugin"
    window = GObject.property(type=Xed.Window)
    notebook = GObject.property(type=Xed.Notebook)
    

    def __init__(self):
        GObject.Object.__init__(self)
        self.temp_dir = os.path.expanduser("~/.xed_temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.temp_files = set()
        self.session_files = {}
        self.session_file = os.path.expanduser("~/.xed_session")
        

    def do_activate(self):
        # Create ~/.xed_temp directory if it doesn't exist
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        self.restore_temp_files()

        # Connect signals
        self.connect_signals()

    def connect_signals(self):
        # Connect signal to handle events
        self.window.connect("delete-event", self.on_window_delete_event)
        notebook = self.get_notebook(self.window)
        if notebook: notebook.connect("tab-close-request", self.close_test)


    def get_notebook(self, window):
        notebook = False
        gtk_overlay = window.get_child()
        if isinstance(gtk_overlay, Gtk.Overlay):
            gtk_overlay_children = gtk_overlay.get_children()
            if len(gtk_overlay_children) > 0:
                gtk_box = gtk_overlay_children[0]
                if isinstance(gtk_box, Gtk.Box):
                    gtk_box_children = gtk_box.get_children()
                    if len(gtk_box_children) > 2:
                        xedpaned = gtk_box_children[2]
                        if str(type(xedpaned)) == "<class '__gi__.XedPaned'>":
                            xedpaned_children = xedpaned.get_children()
                            if len(xedpaned_children) > 1:
                                sub_xedpaned = xedpaned_children[1]
                                if str(type(sub_xedpaned)) == "<class '__gi__.XedPaned'>":
                                    sub_xedpaned_children = sub_xedpaned.get_children()
                                    if len(sub_xedpaned_children) > 0:
                                        notebook_result = sub_xedpaned_children[0]
                                        if isinstance(notebook_result, Xed.Notebook):
                                            notebook = notebook_result
        return notebook


    def on_window_delete_event(self, window, event):
        print("Delete event")
        self.session_files = {}
        for unsaved_doc in Xed.Window.get_unsaved_documents(self.window):
            text = unsaved_doc.get_text(unsaved_doc.get_start_iter(), unsaved_doc.get_end_iter(), True)
            if text:
                path = unsaved_doc.get_location().get_path() if unsaved_doc.get_location() else None
                temp_file_path = os.path.join(self.temp_dir, self.generate_unique_filename(unsaved_doc.get_uri_for_display()) + ".tmp")
                self.session_files[unsaved_doc.get_uri_for_display()] = {
                    "temp_location": temp_file_path,
                    "file_location": path,
                    "short_name": unsaved_doc.get_short_name_for_display(),
                    "saved": False
                }
                self.save_document(unsaved_doc, temp_file_path)


        notebook = self.get_notebook(self.window)
        if notebook:
            for tb in notebook.get_children():
                doc = tb.get_document()
                temp_file_path = os.path.join(self.temp_dir, self.generate_unique_filename(doc.get_uri_for_display()) + ".tmp")
                if not doc.get_uri_for_display() in self.session_files:
                    path = doc.get_location().get_path() if doc.get_location() else None

                    if path:
                        self.session_files[doc.get_uri_for_display()] = {
                            "temp_location": temp_file_path,
                            "file_location": path,
                            "short_name": doc.get_short_name_for_display(),
                            "saved": True
                        }
                
                        self.save_document(doc, temp_file_path)

            temporary_files = {}
            for long_name, values in self.session_files.items():
                temporary_files[values["temp_location"]] = {
                    "long_name": long_name,
                    "file_location": values["file_location"],
                    "short_name": values["short_name"],
                    "saved": values["saved"]
                }

            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if not file_path in temporary_files:
                    os.remove(file_path)

            self.save_session()
            
            for tb in notebook.get_children():
                tb.get_view().destroy()

            Xed.Window.close(window)

    def save_session(self):
        with open(self.session_file, "w") as json_file:
            json.dump(self.session_files, json_file)
    
    def read_session(self):
        try:
            with open(self.session_file, "r") as json_file:
                self.session_files = json.load(json_file)
        except:
            self.session_files = {}


    def close_test(self, notebook, tab):
        print("tab close request")
        pass

    def generate_unique_filename(self,uri):
        # Generate a unique identifier for the temporary file
        hash_object = hashlib.sha256(uri.encode())
        return hash_object.hexdigest()

    def restore_temp_files(self):
        # Iterate through temp directory and open files
        encoding = GtkSource.Encoding.get_utf8()
        self.read_session()
        for file_display_uri in self.session_files:
            temp_location = self.session_files[file_display_uri]["temp_location"]
            file_location = self.session_files[file_display_uri]["file_location"]
            saved = self.session_files[file_display_uri]["saved"]
            
            if not file_location:
                if os.path.exists(temp_location):
                    with open(temp_location, 'r') as f_temp: content = f_temp.read()
                else: content = ""
                stream = Gio.MemoryInputStream.new_from_data(content.encode(), None)
                tab = Xed.Window.create_tab_from_stream(self.window, stream, encoding, True, True)
            else:
                if saved:
                    if os.path.exists(file_location):
                        file = Gio.File.new_for_path(file_location)
                        tab = self.window.create_tab_from_location(file, encoding, 0, True, True)
                else:
                    if os.path.exists(temp_location):
                        with open(temp_location, 'r') as fsaved_temp: content = fsaved_temp.read()
                        stream = Gio.MemoryInputStream.new_from_data(content.encode(), None)
                        tab = Xed.Window.create_tab_from_stream(self.window, stream, encoding, True, True)
                        document = tab.get_document()
                        file = Gio.File.new_for_path(file_location)
                        document.set_location(file)
                        # stream input and set location
                    else:
                        if os.path.exists(file_location):
                            file = Gio.File.new_for_path(file_location)
                            tab = self.window.create_tab_from_location(file, encoding, 0, True, True)
       
    def save_document(self, doc, file_path):
        text = doc.get_text(doc.get_start_iter(), doc.get_end_iter(), True)
        with open(file_path, "w") as f:
            f.write(text)

    def do_deactivate(self):
        pass

    def do_update_state(self):
        pass

def get_plugin():
    return SessionPlugin()
