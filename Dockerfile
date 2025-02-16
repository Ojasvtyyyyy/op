FROM python:3.12-slim

WORKDIR /app

# Install supervisor first
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Create supervisor directory and configuration
RUN mkdir -p /etc/supervisor/conf.d

COPY . .

# Create the supervisor configuration file
RUN echo "[supervisord]\n\
nodaemon=true\n\
\n\
[program:telegram_bot]\n\
command=python bot.py\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
\n\
[program:flask_app]\n\
command=gunicorn -w 4 -b 0.0.0.0:10000 app:app\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0" > /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
