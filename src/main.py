from actor import Actor
from app import App

if __name__ == "__main__":
    romfs_path: str = input("Enter romfs path: ")
    project_path: str = input("Enter mod romfs path: ")

    app = App(project_path, romfs_path)

    base_actor: str = input("Enter base actor name: ")
    new_actor: str = input("Enter new actor name: ")

    actor = Actor.copy(new_actor, base_actor)
    actor.save()