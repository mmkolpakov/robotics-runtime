# ruff: noqa: E402, F401

import os

# ruleid: attach-only-no-process-control
import subprocess

# ruleid: attach-only-no-orchestrator-sdk
import docker

# ruleid: attach-only-no-network-client
import requests


def allowed_helper():
    # ok: attach-only-no-network-client
    from urllib.request import url2pathname


def allowed_helper_alias():
    # ok: attach-only-no-network-client
    from urllib.request import url2pathname as to_path


def forbidden_mixed_import():
    # ruleid: attach-only-no-network-client
    from urllib.request import build_opener, url2pathname


def forbidden_client_import():
    # ruleid: attach-only-no-network-client
    from urllib.request import urlopen


def forbidden_client_alias():
    # ruleid: attach-only-no-network-client
    from urllib.request import urlretrieve as retrieve


def forbidden_module_import():
    # ruleid: attach-only-no-network-client
    import urllib.request


def forbidden_module_alias():
    # ruleid: attach-only-no-network-client
    import urllib.request as client


# ruleid: attach-only-no-mutation-service-types
from lifecycle_msgs.srv import ChangeState


def forbidden_ros_apis(node, client):
    # ruleid: attach-only-no-ros-publisher
    node.create_publisher(object, "/command", 10)
    # ruleid: attach-only-no-action-client
    client.send_goal_async(object())


def forbidden_os_api():
    # ruleid: attach-only-no-process-control
    os.execv("/bin/false", ["false"])


def allowed_observer_apis(node):
    # ok: attach-only-no-ros-publisher
    node.create_subscription(object, "/observation", lambda message: message, 10)
