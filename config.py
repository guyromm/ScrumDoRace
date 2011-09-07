# -*- coding: utf-8 -*-
'''
filedesc: default boilerplate config for a new noodles project
'''
import os

DEBUG = True

# Specify the server port
PORT = 8090
ENCODING = 'utf-8' # default application encoding

APP_DIR = os.getcwd()

# Specify URL resolver module, this must contain get_map function which returnes mapper object
# urls.py module is default
URL_RESOLVER = 'urls'

# Specify controllers modules
CONTROLLERS = ['controllers', 'static']

# Specify Redis-server host there
REDIS_HOST = 'localhost'

# Specify root dir for static content here
STATIC_ROOT = os.path.join(os.getcwd(), 'static')

# Specify here a template directories
TEMPLATE_DIRS = [
        os.path.join(APP_DIR, 'templates'),
# Add here other directories if you need
    ]

# Specify here mako temporary dir for precompiled templates
MAKO_TMP_DIR = os.path.join(APP_DIR, 'tmp/modules')

MIDDLEWARES = [
               # Specify list of middlewares used in your application here
               #'session.SessionMiddleware', 
               ]

SERVER_LOGTYPE='default'

from local_settings import *
