# -*- coding: utf-8 -*-
'''
filedesc: default url mapping
'''
from routes import Mapper
from config import DEBUG
from noodles.maputils import urlmap

def get_map():
    " This function returns mapper object for dispatcher "
    map = Mapper()
    # Add routes here
    urlmap(map, [
                 
                ('/', 'controllers.index'),
                #('/route/url', 'controllerName.actionName')     
            ])
    
    # Old style map connecting 
    #map.connect('Route_name', '/route/url', controller='controllerName', action='actionName')
    map.connect('/iteration/{iteration_id}',controller='controllers',action='iteration')
    map.connect('/all',controller='controllers',action='iteration')
    if DEBUG:
        map.connect(None, '/static/{path_info:.*}', controller='static', action='index') #Handling static files

    return map

