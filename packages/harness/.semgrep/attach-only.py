# ruff: noqa: E402, F401

import os

# ruleid: attach-only-no-process-control
import subprocess

# ok: attach-only-no-network-client
# ruleid: attach-only-no-network-client
from urllib.request import url2pathname, urlopen

# ruleid: attach-only-no-network-client
from urllib.request import urlretrieve as retrieve

# ruleid: attach-only-no-orchestrator-sdk
import docker

# ruleid: attach-only-no-network-client
import requests


def forbidden_mixed_import():
    # ruleid: attach-only-no-network-client
    from urllib.request import build_opener


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
