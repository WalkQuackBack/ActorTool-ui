from actor import Actor
from app import App

import dearpygui.dearpygui as dpg
import tkinter.filedialog

def open_dir(sender, app_data, user_data):
    if user_data == "romfs":
        dpg.set_value("romfs", tkinter.filedialog.askdirectory())
    else:
        dpg.set_value("project", tkinter.filedialog.askdirectory())

def save(sender, app_data, user_data):
    if dpg.get_value(user_data["romfs"]) == "" or dpg.get_value(user_data["project"]) == "":
        return
    if dpg.get_value(user_data["base"]) == "" or dpg.get_value(user_data["actor"]) == "":
        return
    with dpg.window():
        dpg.add_text(tag="Message", default_value="Saving...")
    app = App(dpg.get_value(user_data["project"]), dpg.get_value(user_data["romfs"]))
    actor = Actor.copy(dpg.get_value(user_data["actor"]), dpg.get_value(user_data["base"]))
    actor.save()
    app.save()
    dpg.set_value("Message", "Finished saving")

def init_dpg():
    dpg.create_context()

    with dpg.window(tag="MainWindow", min_size=(800, 220)) as window:
        dpg.add_button(label="Select romfs path", callback=open_dir, pos=(20, 20), width=160, height=20, user_data="romfs")
        romfs = dpg.add_text(tag="romfs", pos=(190, 20), default_value="")
        dpg.add_button(label="Select project path", callback=open_dir, pos=(20, 50), width=160, height=20, user_data="project")
        project = dpg.add_text(tag="project", pos=(190, 50), default_value="")
        base = dpg.add_input_text(label="Base Actor Name", pos=(20, 80), width=550, height=20)
        actor = dpg.add_input_text(label="New Actor Name", pos=(20, 110), width=550, height=20)
        dpg.add_button(label="Save",
                       callback=save,
                       user_data={"romfs" : romfs, "project" : project, "base" : base, "actor" : actor},
                       pos=(20, 140))

    dpg.create_viewport(title="Very Bad UI", min_width=800, min_height=220, width=900, height=220)
    dpg.setup_dearpygui()
    dpg.set_primary_window(window, True)

if __name__ == "__main__":
    init_dpg()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()