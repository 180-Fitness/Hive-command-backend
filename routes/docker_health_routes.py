from flask import Blueprint

from controllers import docker_health_controller

docker = Blueprint("docker", __name__)


@docker.route("/health", methods=["GET"])
def check_health():
    return docker_health_controller.check_health()
