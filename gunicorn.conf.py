import os

# Bind to the port specified by Render
port = int(os.environ.get("PORT", 10000))
bind = f"0.0.0.0:{port}"

# Worker configuration
workers = 2
threads = 4
timeout = 120

# Access log configuration
accesslog = "-"
errorlog = "-"
