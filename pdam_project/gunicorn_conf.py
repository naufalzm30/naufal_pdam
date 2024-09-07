import multiprocessing

# Bind address and port
bind = '213.210.21.73:8001'

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Maximum requests per worker
max_requests = 1000

# Timeout for worker processes
timeout = 30

# Specify the path to your Django application's WSGI application
# Replace 'your_project' with the name of your Django project directory
# Replace 'your_project.wsgi:application' with the path to your WSGI application
app = 'pdam_project.wsgi:application'

# Optionally, specify the Django settings module explicitly
env = {
    'DJANGO_SETTINGS_MODULE': 'pdam_project.settings',
}
