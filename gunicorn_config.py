import os

loglevel = "info"
errorlog = "-"
accesslog = "-"
graceful_timeout = 120
timeout = 120
keepalive = 5
threads = 4
bind = f"0.0.0.0:{os.environ.get('PORT', '8090')}"
workers = 4
