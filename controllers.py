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
from github_commits import compile_report


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
def iteration(request,iteration_id=None,how='bypoints'):
    if iteration_id=='None': iteration_id=None
    c2 = conn.cursor(my.cursors.DictCursor)
    if iteration_id=='current':
        res = c2.execute("select id from projects_iteration where project_id=%s and start_date<=now() and end_date>=now()",PROJECT_ID)
        iteration_id = c2.fetchone()['id']

    if iteration_id:
        res = c2.execute("select start_date,end_date from projects_iteration where id=%s",iteration_id)
        start_date,end_date = c2.fetchone().values()
    else:
        start_date=None
        end_date=None
    print 'running for dates %s - %s'%(start_date,end_date)
    if how=='bydiff':
        commits = compile_report.run(start_date=start_date,end_date=end_date,makereport=False)
    else:
        commits ={'by_story':{}}

    likey= '%commited to github%'
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
    for st in stories:
        print('checking if story %s is in %s'%(st['local_id'],commits['by_story'].keys()))
        if unicode(st['local_id']) in commits['by_story'].keys():
            st['diff']= commits['by_story'][unicode(st['local_id'])]['diff']
        else:
            st['diff']=0


    fqry2 = "select u.email,sum(s.points) points,count(*) stories %s group by u.email"%joinqry
    if iteration_id:
        res = c2.execute(fqry2,qa2)
    else:
        res = c2.execute(fqry2,qa2)
    points = c2.fetchall()
    try:
        if how=='bydiff':
            maxpoints=sum([df['diff'] for df in commits['by_story'].values()])
        else:
            maxpoints=max([p['points'] for p in points])
    except ValueError:
        maxpoints=0
    c = conn.cursor()
    if iteration_id:
        itername = getiterationname(c,iteration_id)
    else:
        itername = 'all iterations'
    return render_to_response('/iteration.html',{'maxpoints':json.dumps(maxpoints),'points':json.dumps(points),'stories':json.dumps(stories),'SCRUMDO_BASEURL':SCRUMDO_BASEURL,'projectname':getprojectname(c),'iteration_id':iteration_id,'iteration_name':itername,'how':how},request)
