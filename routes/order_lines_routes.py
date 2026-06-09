from flask import Blueprint, request

import controllers

order_lines = Blueprint("order_lines", __name__)


@order_lines.route("/task/<task_id>/order-lines", methods=["GET"])
def order_lines_by_task_get(task_id):
    return controllers.order_lines_by_task_get(request, task_id)


@order_lines.route("/proofpix/orders/import", methods=["POST"])
def proofpix_orders_import():
    return controllers.proofpix_orders_import(request)
