# -*- coding: utf-8 -*-
'''
filedesc: default controller file
'''
import json
from noodles.templates import render_to_response
from noodles.http import Response
import MySQLdb as my
args = json.loads(open('mysql.json','r').read())
conn = my.connect(**args)

from config import PROJECT_ID,SCRUMDO_BASEURL

def getprojectname(c):
    res = c.execute("select name from projects_project where id=%s",PROJECT_ID)
    return c.fetchone()[0]

def getiterationname(c,iteration_id):
    res = c.execute("select name from projects_iteration where id=%s",iteration_id)
    return c.fetchone()[0]

def index(request):
    qry="select * from projects_iteration where project_id=%s order by cast(name as signed)"
    c = conn.cursor()
    c2 = conn.cursor(my.cursors.DictCursor)
    projectname = getprojectname(c)
    res = c.execute(qry,PROJECT_ID)
    iters = c.fetchall()
    #raise Exception('PROJECT %s iters: %s'%(PROJECT_ID,iters))
    return render_to_response('/index.html',{'iterations':iters,'SCRUMDO_BASEURL':SCRUMDO_BASEURL,'projectname':projectname},request)
def iteration(request,iteration_id=None):
    c2 = conn.cursor(my.cursors.DictCursor)
    likey= 'github commit%'
    joinqry =  "from projects_story s,auth_user u where u.id=s.assignee_id"
    if iteration_id: 
        joinqry+=" and iteration_id=%s "
        qargs = [likey,iteration_id]
        qa2 = [iteration_id]
    else:
        joinqry+=" and iteration_id in (select id from projects_iteration where project_id=%s)"
        qargs= [likey,str(PROJECT_ID)]
        qa2 = [PROJECT_ID]
    fnames = 's.id,s.local_id,s.summary,s.status,s.points,s.rank,u.email'
    fqry = "select %s\n,(select count(*) from threadedcomments_threadedcomment where comment like TOKEN and object_id=s.id) commits,count(*) commits\n %s \n group by %s \n order by assignee_id,rank"%(fnames,joinqry,fnames)
    fqry=fqry.replace('TOKEN','%s')
    print fqry
    print qargs
    if iteration_id:
        res = c2.execute(fqry.replace('\n',''),qargs)
    else:
        res = c2.execute(fqry,qargs)
    stories = c2.fetchall()
    fqry2 = "select u.email,sum(s.points) points,count(*) stories %s group by u.email"%joinqry
    if iteration_id:
        res = c2.execute(fqry2,qa2)
    else:
        res = c2.execute(fqry2,qa2)
    points = c2.fetchall()
    maxpoints = max([p['points'] for p in points])
    c = conn.cursor()
    if iteration_id:
        itername = getiterationname(c,iteration_id)
    else:
        itername = 'all iterations'
    return render_to_response('/iteration.html',{'maxpoints':json.dumps(maxpoints),'points':json.dumps(points),'stories':json.dumps(stories),'SCRUMDO_BASEURL':SCRUMDO_BASEURL,'projectname':getprojectname(c),'iteration_id':iteration_id,'iteration_name':itername},request)
