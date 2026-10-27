# Gunicorn shu faylni ishga tushgan papkadan (/app) o'zi o'qiydi — compose va
# Dockerfile'dagi buyruq o'zgarmaydi.
#
# Har bir so'rov davomiyligi bilan logga yoziladi:
#   docker compose logs -f backend
#   [27/Oct/2026:15:24:01 +0500] 200 33ms "GET /api/v1/tickets/5/?mode=study HTTP/1.0" 34512B 1.2.3.4
# Haqiqiy mijoz IP'si nginx'ning X-Real-IP sarlavhasidan olinadi.

accesslog = "-"
access_log_format = '%(t)s %(s)s %(M)sms "%(r)s" %(b)sB %({x-real-ip}i)s'
