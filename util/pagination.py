import config


def pagination_args(request):
    page = request.args.get("page", config.default_start_page, type=int)
    per_page = request.args.get("per_page", config.max_per_page_default, type=int)
    return page, per_page
