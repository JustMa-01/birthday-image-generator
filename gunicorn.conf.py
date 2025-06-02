import os
import multiprocessing

# Bind to the port specified by Render
port = int(os.environ.get("PORT", 10000))
bind = f"0.0.0.0:{port}"

# Worker configuration
workers = multiprocessing.cpu_count()
worker_class = 'gthread'
threads = 4
worker_connections = 1000
timeout = 300
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# SSL Configuration
keyfile = None
certfile = None

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Process Naming
proc_name = None

# Server Hooks
def on_starting(server):
    print("Server is starting...")
