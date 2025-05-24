import copy
import os
import toml
from pathlib import Path

from taskgraph.transforms.base import TransformSequence

transforms = TransformSequence()


@transforms.add
def generate_tasks(config, tasks):
    for task in tasks:
        env = task["worker"].setdefault("env", {})
        yield from create_tasks_for_all(config, task)


def create_task_for_apworld(config, original_task, world_name, apworld_name, version, ap_dependencies, latest, previous_version, chained):
    task = copy.deepcopy(original_task)
    env = task["worker"].setdefault("env", {})
    env["TEST_WORLD_NAME"] = world_name
    env["TEST_APWORLD_NAME"] = apworld_name
    env["TEST_APWORLD_VERSION"] = version
    task["label"] = f"{config.kind}-{apworld_name}-{version}"
    task.setdefault("attributes", {})["latest"] = latest
    task.setdefault("attributes", {})["apworld_name"] = apworld_name

    dependencies = [f"{dep}-{apworld_name}-{version}" for dep in ap_dependencies]
    for dep in dependencies:
        task.setdefault("soft-dependencies", []).append(dep)

    if chained and previous_version:
        dep = f"{config.kind}-{apworld_name}-{previous_version}"
        task.setdefault("soft-dependencies", []).append(dep)
        env["PREVIOUS_TASK"] = {"task-reference": f"<{dep}>"}

    return task


def create_tasks_for_all(config, task):
    index = toml.load("index.toml")
    ap_deps = task.pop('ap-deps', [])
    chained = task.pop('chained', False)
    for world_path in os.listdir("index/"):
        world = toml.load(os.path.join("index", world_path))
        if world.get("disabled"):
            continue

        world_name = world["name"]

        apworld_name = Path(world_path).stem
        versions = list(world.get("versions", {}).keys()) # TODO: Sort those probably
        if world.get("supported", False):
            versions.append(index["archipelago_version"])

        previous_version = None
        for i, version in enumerate(versions):
            latest = i == (len(versions) - 1)
            yield create_task_for_apworld(config, task, world_name, apworld_name, version, ap_deps, latest, previous_version, chained)
            previous_version = version

