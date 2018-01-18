#!/usr/bin/python2

# Workspace switcher dockbarx applet
# Copyright 2018 (c) Sergey Hayevoy <jantao.dev@gmail.com>

import wnck, sys, gtk, cairo
from dockbarx.applets import DockXApplet #, DockXAppletDialog 


class Desk:

    def __init__(self, workspace):
        self.parent = workspace

    def is_active(self):
        return self.parent.get_screen().get_active_workspace() == self.parent

    def activate(self):
        self.parent.activate(gtk.get_current_event_time())


class VirtualDesk:

    def __init__(self, workspace, left, top):
        self.parent = workspace
        self.top = top
        self.left = left

    def is_active(self):
        active_workspace = self.parent.get_screen().get_active_workspace()
        return active_workspace.get_viewport_x() == self.left and active_workspace.get_viewport_y() == self.top

    def activate(self):
        if self.parent.get_screen().get_active_workspace() != self.parent:
            self.parent.activate(gtk.get_current_event_time())
        self.parent.get_screen().move_viewport(self.left, self.top)


class WorkspaceSwitcherApplet(DockXApplet):

    icon_padding = 3

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)

        self.image = gtk.Image()
        self.add(self.image)
        self.image.show()
        self.show()
        self.screen = wnck.screen_get_default()
        while gtk.events_pending():
            gtk.main_iteration()
        self.update()
        self.connect("scroll-event", self.on_scroll)
        self.screen.connect("active-workspace-changed", self.on_active_workspace_changed)
        self.screen.connect("viewports-changed", self.on_viewports_changed)
        self.screen.connect("workspace-created", self.on_workspace_created)
        self.screen.connect("workspace-destroyed", self.on_workspace_destroyed)
        self.connect("button-press-event", self.on_click)

    def update(self):
        dockx_globals = self.dockx_r().globals
        self.dockx_orient = dockx_globals.settings["dock/position"]
        self.dockx_size = dockx_globals.settings["dock/size"]
        try:
            del self.surface
        except AttributeError:
            pass
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.dockx_size, self.dockx_size)
        self.update_workspaces()
        self.update_context_menu()
        self.update_icon()

    def update_workspaces(self):
        workspaces = self.screen.get_workspaces()
        if len(workspaces) == 1 and workspaces[0].is_virtual():
            workspace = workspaces[0]
            desc_width = workspace.get_screen().get_width()
            desc_height = workspace.get_screen().get_height()
            self.rows = workspace.get_height() / desc_height
            self.cols = workspace.get_width() / desc_width
            self.wall = {}
            for x in range(self.cols):
                self.wall[x] = {}
                for y in range(self.rows):
                    self.wall[x][y] = VirtualDesk(workspace, x * desc_width, y * desc_height)
        else:
            self.rows = 1
            self.cols = 1
            self.wall = {}
            for workspace in workspaces:
                x = workspace.get_layout_column()
                y = workspace.get_layout_row()
                if not self.wall.has_key(x):
                    self.wall[x] = {}
                self.wall[x][y] = Desk(workspace)
                self.cols = max(self.cols, x + 1)
                self.rows = max(self.rows, y + 1)
        self.update_context_menu()
        self.update_active_workspace()

    def update_active_workspace(self):
        self.active_row = 0
        self.active_col = 0
        for x in range(self.cols):
            for y in range(self.rows):
                try:
                    if self.wall[x][y].is_active():
                        self.active_col = x
                        self.active_row = y
                except NameError:
                    pass

    def update_icon(self):
        step_x = int((self.dockx_size + self.icon_padding) / self.cols)
        step_y = int((self.dockx_size + self.icon_padding) / self.rows)
        cr = cairo.Context(self.surface)
        for x in range(self.cols):
            for y in range(self.rows):
                if (x == self.active_col) and (y == self.active_row):
                    cr.set_source_rgb(1, 1, 1)
                else:
                    cr.set_source_rgb(0, 0.1, 0)
                cr.rectangle(x * step_x, y * step_y, step_x - self.icon_padding, step_y - self.icon_padding)
                cr.fill()
        pixbuf = gtk.gdk.pixbuf_new_from_data(self.surface.get_data(), gtk.gdk.COLORSPACE_RGB, True, 8, self.dockx_size, self.dockx_size, self.surface.get_stride())
        self.image.set_from_pixbuf(pixbuf)

    def update_context_menu(self):
        menu = gtk.Menu()
        for x in range(self.cols):
            for y in range(self.rows):
                item = gtk.MenuItem("Desktop [%d,%d]" % (x + 1, y + 1))
                item.connect("activate", self.on_context_menu_click, [x, y])
                item.show_all()
                menu.append(item)
        #separator = gtk.SeparatorMenuItem()
        #separator.show_all()
        #menu.append(separator)
        #preference_item = gtk.MenuItem(_("Preference"))
        #preference_item.connect("activate", self.show_preferences_cb)
        #preference_item.show_all()
        #menu.append(preference_item)
        self.menu = menu

    def change_desk(self, direction):
        self.active_row = self.active_row + direction
        if self.active_row >= self.rows:
            self.active_row = 0
            self.active_col = self.active_col + direction
        elif self.active_row < 0:
            self.active_row = self.rows - 1
            self.active_col = self.active_col + direction
        if self.active_col >= self.cols:
            self.active_col = 0
        elif self.active_col < 0:
            self.active_col = self.cols - 1
        try:
            self.wall[self.active_col][self.active_row].activate()
        except NameError:
            pass
        self.update_icon()

    def on_click(self, widget, event):
        if event.button == 1:
            step_x = int((self.dockx_size + self.icon_padding) / self.cols)
            step_y = int((self.dockx_size + self.icon_padding) / self.rows)
            x = event.x // step_x
            y = event.y // step_y
            if (event.x % step_x <= step_x - self.icon_padding) and (event.y % step_y <= step_y - self.icon_padding) and (x < self.cols) and (y < self.rows):
                self.active_col = x
                self.active_row = y
                try:
                    self.wall[self.active_col][self.active_row].activate()
                except NameError:
                    pass
                self.update_icon()
        elif event.button == 2:
            pass
        elif event.button == 3:
            self.menu.popup(None, None, None, event.button, event.time)

    def on_context_menu_click(self, widget, data):
        self.active_col = data[0]
        self.active_row = data[1]
        try:
            self.wall[self.active_col][self.active_row].activate()
        except NameError:
            pass
        self.update_icon()

    def on_scroll(self, widget, event):
        if event.direction == gtk.gdk.SCROLL_UP:
            self.change_desk(-1)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            self.change_desk(1)

    def on_active_workspace_changed(self, screen, workspace):
        self.update_active_workspace()
        self.update_icon()

    def on_viewports_changed(self, screen):
        self.update_active_workspace()
        self.update_icon()

    def on_workspace_created(self, screen, workspace):
        self.update_workspaces()
        self.update_icon()

    def on_workspace_destroyed(self, screen, workspace):
        self.update_workspaces()
        self.update_icon()

def get_dbx_applet(dbx_dict):
    applet = WorkspaceSwitcherApplet(dbx_dict)
    return applet

