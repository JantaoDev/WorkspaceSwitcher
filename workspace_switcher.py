#!/usr/bin/python2

# Workspace switcher DockbarX applet
# Copyright 2018 (c) Sergey Hayevoy <jantao.dev@gmail.com>
#
# https://github.com/JantaoDev/WorkspaceSwitcher
# The code is under GPL3 license.

import wnck, sys, gtk, cairo
from dockbarx.applets import DockXApplet, DockXAppletDialog 

CFG_SCROLL_ENABLED = True
CFG_COLOR = "0,0,0,0.1"
CFG_ACTIVE_COLOR = "1,1,1,1"
CFG_PADDING = 0
CFG_CELL_SPACING = 3
CFG_DESK_NAME_PATTERN = "Workspace %n [%x,%y]"
CFG_ASPECT_RATIO = 1

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

    def __init__(self, dbx_dict):
        DockXApplet.__init__(self, dbx_dict)

        self.image = gtk.Image()
        self.add(self.image)
        self.image.show()
        self.show()
        self.screen = wnck.screen_get_default()
        while gtk.events_pending():
            gtk.main_iteration()

        self.cfg_scroll_enabled = self.get_setting("scroll_enabled", CFG_SCROLL_ENABLED)
        self.cfg_active_color = self.get_setting("active_color", CFG_ACTIVE_COLOR)
        self.cfg_color = self.get_setting("color", CFG_COLOR)
        self.cfg_cell_spacing = self.get_setting("cell_spacing", CFG_CELL_SPACING)
        self.cfg_padding = self.get_setting("padding", CFG_PADDING)
        self.cfg_desk_name_pattern = self.get_setting("desk_name_pattern", CFG_DESK_NAME_PATTERN)
        self.cfg_aspect_ratio = self.get_setting("aspect_ratio", CFG_ASPECT_RATIO)

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
        self.dockx_size = max(dockx_globals.settings["dock/size"], 16)
        if self.dockx_orient in ["left", "right"]:
            self.icon_width = int(self.dockx_size)
            self.icon_height = int(self.dockx_size * self.cfg_aspect_ratio)
        else:
            self.icon_width = int(self.dockx_size / self.cfg_aspect_ratio)
            self.icon_height = int(self.dockx_size)
        try:
            del self.surface
        except AttributeError:
            pass
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.icon_width, self.icon_height)
        self.update_workspaces()
        self.update_context_menu()
        self.update_icon()

    def update_workspaces(self):
        self.workspaces_count = self.screen.get_workspace_count()
        self.workspaces_width = self.screen.get_active_workspace().get_width()
        self.workspaces_height = self.screen.get_active_workspace().get_height()
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
        step_x = float(self.icon_width - self.cfg_padding * 2 + self.cfg_cell_spacing) / self.cols
        step_y = float(self.icon_height - self.cfg_padding * 2 + self.cfg_cell_spacing) / self.rows
        if (step_x < 1) or (step_y < 1):
            return
        col = map(float, self.cfg_color.split(','))
        acol = map(float, self.cfg_active_color.split(','))
        cr = cairo.Context(self.surface)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.rectangle(0, 0, self.icon_width, self.icon_height)
        cr.fill()
        for x in range(self.cols):
            for y in range(self.rows):
                if (x == self.active_col) and (y == self.active_row):
                    cr.set_source_rgba(acol[2], acol[1], acol[0], acol[3])
                else:
                    cr.set_source_rgba(col[2], col[1], col[0], col[3])
                xpos = self.cfg_padding + x * step_x
                ypos = self.cfg_padding + y * step_y
                cr.rectangle(round(xpos), round(ypos), round(xpos + step_x) - round(xpos) - self.cfg_cell_spacing, round(ypos + step_y) - round(ypos) - self.cfg_cell_spacing)
                cr.fill()
        pixbuf = gtk.gdk.pixbuf_new_from_data(self.surface.get_data(), gtk.gdk.COLORSPACE_RGB, True, 8, self.icon_width, self.icon_height, self.surface.get_stride())
        self.image.set_from_pixbuf(pixbuf)

    def update_context_menu(self):
        menu = gtk.Menu()
        for x in range(self.cols):
            for y in range(self.rows):
                deskname = self.cfg_desk_name_pattern.replace('%x', str(x + 1)).replace('%y', str(y + 1)).replace('%n', str(x + y * self.cols + 1))
                item = gtk.MenuItem(deskname)
                item.connect("activate", self.on_context_menu_click, [x, y])
                item.show_all()
                menu.append(item)
        separator = gtk.SeparatorMenuItem()
        separator.show_all()
        menu.append(separator)
        preference_item = gtk.MenuItem("Preferences")
        preference_item.connect("activate", self.on_context_menu_open_preferences)
        preference_item.show_all()
        menu.append(preference_item)
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
            step_x = float(self.icon_width - self.cfg_padding * 2 + self.cfg_cell_spacing) / self.cols
            step_y = float(self.icon_height - self.cfg_padding * 2 + self.cfg_cell_spacing) / self.rows
            if (step_x < 1) or (step_y < 1):
                return
            x = (event.x - self.cfg_padding) / step_x
            y = (event.y - self.cfg_padding) / step_y
            ox = (1 - x + int(x)) * step_x
            oy = (1 - y + int(y)) * step_y
            if (ox > self.cfg_cell_spacing) and (oy > self.cfg_cell_spacing) and (x < self.cols) and (y < self.rows) and (x >= 0) and (y >= 0):
                self.active_col = int(x)
                self.active_row = int(y)
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

    def on_context_menu_open_preferences(self, *args):
        run_applet_dialog('Workspace switcher')

    def on_setting_changed(self, key, value):
        if key == "scroll_enabled":
            self.cfg_scroll_enabled = value
        if key == "active_color":
            self.cfg_active_color = value
        if key == "color":
            self.cfg_color = value
        if key == "cell_spacing":
            self.cfg_cell_spacing = value
        if key == "padding":
            self.cfg_padding = value
        if key == "desk_name_pattern":
            self.cfg_desk_name_pattern = value
        if key == "aspect_ratio":
            self.cfg_aspect_ratio = value
        self.update()

    def on_scroll(self, widget, event):
        if not self.cfg_scroll_enabled:
            return
        if event.direction == gtk.gdk.SCROLL_UP:
            self.change_desk(-1)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            self.change_desk(1)

    def on_active_workspace_changed(self, screen, workspace):
        self.update_active_workspace()
        self.update_icon()

    def on_viewports_changed(self, screen):
        aw = screen.get_active_workspace()
        if (self.workspaces_count != screen.get_workspace_count()) or \
           (self.workspaces_count == 1 and (self.workspaces_width != aw.get_width() or self.workspaces_height != aw.get_height())):
            self.update_workspaces()
        else:
            self.update_active_workspace()
        self.update_icon()

    def on_workspace_created(self, screen, workspace):
        self.update_workspaces()
        self.update_icon()

    def on_workspace_destroyed(self, screen, workspace):
        self.update_workspaces()
        self.update_icon()


class WorkspaceSwitcherAppletPreferences(DockXAppletDialog):
    Title = "Workspace Switcher Applet Preferences"
    
    def __init__(self, applet_name):
        DockXAppletDialog.__init__(self, applet_name)
        
        table = gtk.Table(7, 3)
        table.set_border_width(5)
        table.set_homogeneous(True)
        table.set_col_spacings(15)
        self.vbox.pack_start(table)
        
        self.scroll_enabled_btn = gtk.CheckButton("Change workspaces by mouse scroll")
        self.scroll_enabled_btn.connect("toggled", self.on_checkbox_toggle, "scroll_enabled")
        table.attach(self.scroll_enabled_btn, 0, 2, 0, 1)
        
        label = gtk.Label("Color")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 2, 1, 2)
        self.color_btn = gtk.ColorButton()
        self.color_btn.set_title("Color")
        self.color_btn.set_use_alpha(True)
        self.color_btn.connect("color-set", self.on_color_set, "color")
        table.attach(self.color_btn, 2, 3, 1, 2)

        label = gtk.Label("Active color")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 2, 2, 3)
        self.active_color_btn = gtk.ColorButton()
        self.active_color_btn.set_title("Active color")
        self.active_color_btn.set_use_alpha(True)
        self.active_color_btn.connect("color-set", self.on_color_set, "active_color")
        table.attach(self.active_color_btn, 2, 3, 2, 3)

        label = gtk.Label("Padding")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 3, 4)
        self.padding_input = gtk.HScale()
        self.padding_input.set_digits(0)
        self.padding_input.set_range(0, 10)
        self.padding_input.set_increments(1, 5)
        self.padding_input.connect("change-value", self.on_range_value_set, "padding")
        table.attach(self.padding_input, 1, 3, 3, 4)

        label = gtk.Label("Cell spacing")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 4, 5)
        self.cell_spacing_input = gtk.HScale()
        self.cell_spacing_input.set_digits(0)
        self.cell_spacing_input.set_range(0, 10)
        self.cell_spacing_input.set_increments(1, 5)
        self.cell_spacing_input.connect("change-value", self.on_range_value_set, "cell_spacing")
        table.attach(self.cell_spacing_input, 1, 3, 4, 5)

        label = gtk.Label("Aspect ratio")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 5, 6)
        self.aspect_ratio_input = gtk.HScale()
        self.aspect_ratio_input.set_digits(1)
        self.aspect_ratio_input.set_range(0.3, 3.0)
        self.aspect_ratio_input.set_increments(0.1, 1)
        self.aspect_ratio_input.connect("change-value", self.on_range_value_set, "aspect_ratio")
        table.attach(self.aspect_ratio_input, 1, 3, 5, 6)

        label = gtk.Label("Workspace name pattern")
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, 6, 7)
        self.desk_name_pattern_input = gtk.Entry()
        self.desk_name_pattern_input.set_tooltip_text("%n - workspace number\n%x - workspace column\n%y - workspace row")
        self.desk_name_pattern_input.connect("changed", self.on_entry_value_set, "desk_name_pattern")
        table.attach(self.desk_name_pattern_input, 1, 3, 6, 7)

        self.show_all()

    def run(self):
        self.scroll_enabled_btn.set_active(self.get_setting("scroll_enabled", CFG_SCROLL_ENABLED))
        
        col_raw = self.get_setting("color", CFG_COLOR)
        col = map(float, col_raw.split(','))
        self.color_btn.set_color(gtk.gdk.Color(int(col[0] * 65535), int(col[1] * 65535), int(col[2] * 65535)))
        self.color_btn.set_alpha(int(col[3] * 65535))
        
        acol_raw = self.get_setting("active_color", CFG_ACTIVE_COLOR)
        acol = map(float, acol_raw.split(','))
        self.active_color_btn.set_color(gtk.gdk.Color(int(acol[0] * 65535), int(acol[1] * 65535), int(acol[2] * 65535)))
        self.active_color_btn.set_alpha(int(acol[3] * 65535))
        
        self.padding_input.set_value(self.get_setting("padding", CFG_PADDING))
        self.cell_spacing_input.set_value(self.get_setting("cell_spacing", CFG_CELL_SPACING))
        self.aspect_ratio_input.set_value(self.get_setting("aspect_ratio", CFG_ASPECT_RATIO))
        self.desk_name_pattern_input.set_text(self.get_setting("desk_name_pattern", CFG_DESK_NAME_PATTERN))

        return DockXAppletDialog.run(self)

    def on_checkbox_toggle(self, widget, key):
        if key == "scroll_enabled":
            self.set_setting("scroll_enabled", widget.get_active())

    def on_color_set(self, widget, key):
        col = widget.get_color()
        a = float(widget.get_alpha())
        val = map(str, [col.red_float, col.green_float, col.blue_float, a / 65535])
        if key in ["color", "active_color"]:
            self.set_setting(key, ','.join(val))

    def on_range_value_set(self, widget, scroll, value, key):
        if key in ["padding", "cell_spacing", "aspect_ratio"]:
            self.set_setting(key, value)

    def on_entry_value_set(self, widget, key):
        if key == "desk_name_pattern":
            self.set_setting(key, widget.get_text())

def get_dbx_applet(dbx_dict):
    applet = WorkspaceSwitcherApplet(dbx_dict)
    return applet

def run_applet_dialog(name):
    dialog = WorkspaceSwitcherAppletPreferences(name)
    dialog.run()
    dialog.destroy()
