FROM python:3.12-slim

WORKDIR /app

# Install supervisor and its dependencies
RUN apt-get update && \
    apt-get install -y supervisor procps && \
    mkdir -p /var/log/supervisor && \
    mkdir -p /var/run && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Create supervisor directory
RUN mkdir -p /etc/supervisor/conf.d

COPY . .

# Create the supervisor configuration file
RUN echo "[supervisord]\n\
nodaemon=true\n\
logfile=/var/log/supervisor/supervisord.log\n\
pidfile=/var/run/supervisord.pid\n\
\n\
[program:telegram_bot]\n\
command=python bot.py\n\
directory=/app\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
\n\
[program:flask_app]\n\
command=gunicorn -w 4 -b 0.0.0.0:10000 app:app\n\
directory=/app\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0" > /etc/supervisor/conf.d/supervisord.conf

# Verify supervisor installation and print the binary path
RUN which supervisord && supervisord --version

# Use the correct path to supervisord
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
