# -*- coding: utf-8 -*-
'''
filedesc: default controller file
'''
import json
from noodles.templates import render_to_response,render_to_string
from noodles.http import Response
import MySQLdb as my
args = json.loads(open('mysql.json','r').read())
conn = my.connect(**args)
from github_commits import compile_report
from orm import *
from noodles.http import Redirect

from config import PROJECT_ID,SCRUMDO_BASEURL

def getprojectname(c):
    res = c.execute("select name from projects_project where id=%s",PROJECT_ID)
    return c.fetchone()[0]

def getiterationname(c,iteration_id):
    res = c.execute("select name from projects_iteration where id=%s",iteration_id)
    return c.fetchone()[0]

def aspect(request,aspect):
    ni = request.params.get('new_item')
    if ni:
        i = Item()
        i.name = ni
        session.add(i) ; session.commit()
    ns = request.params.get('new_situation')
    if ns:
        i = Situation()
        i.name = ns
        session.add(i) ; session.commit()

    a = session.query(Aspect).get(aspect)
    viewitems = request.params.getall('item')
    if len(viewitems):
        return Redirect("/support/%s/%s"%(a.name,",".join(viewitems)))

    items = session.query(Item).order_by(Item.name).all()
    situations = session.query(Situation).all()
    
    return render_to_response('/item_choice.html',{'aspect':a,'items':items,'situations':situations})

def items(request,aspect,items_str,new_situation=None,new_item=None,observation_id=None):
    swa = request.params.get('switch_aspect')
    if swa:
        return Redirect('/support/%s/%s'%(swa,items_str))
    setcookie={}
    aspects = session.query(Aspect).all()
    a = session.query(Aspect).get(aspect)
    item_objs = session.query(Item).filter(Item.name.in_(items_str.split(','))).all()
    msg=''
    obsby = request.cookies.get('observation_by','')
    if (new_situation and new_item) or observation_id:
        #Raise Exception('new_sit: %s, new_it: %s, obs_id: %s'%(new_situation,new_item,observation_id))
        if observation_id:
            exob = session.query(Observation).get(observation_id)
            if request.params.get('delete_observation'):
                if exob:
                    session.delete(exob) ; session.commit()
                return Redirect('/support/%s/%s'%(aspect,items_str))
            new_situation = exob.situation
            new_item = exob.item
            vals = {'gravity':exob.gravity,'content':exob.content,'observed_by':exob.observed_by}
        else:
            vals = {'gravity':'','content':'','observed_by':obsby}
        err={'observed_by':'','gravity':'','content':''}

        og = request.params.get('observation_gravity',vals['gravity'])
        if og not in gravities: err['gravity']='must select gravity'
        ob = request.params.get('new_observation_by',vals['observed_by'])
        if not ob: err['observed_by']='must specify observer'
        oc = request.params.get('observation_content',vals['content'])
        if not oc: err['content']='must type in an observation'
        vals={'gravity':og,'content':oc,'observed_by':ob}

        if len([er for er in err.values() if er!=''])==0:
            if observation_id:
                o = exob
            else:
                o = Observation()
                o.item = new_item
                if o.item=='ALL': o.item=None
                o.situation = new_situation
                if o.situation=='ALL': o.situation=None
            o.gravity = og
            o.content = oc
            o.observed_by = ob
            o.aspect = a.name
            
            if not observation_id:
                setcookie = {'observation_by':request.params.get('new_observation_by')}
                session.add(o) ; 
                msg='Succesfull inserted'
            else:
                msg='Succesfully updated'
            session.commit()
        #raise Exception('%s from %s'%(vals,request.params))
        new_form=True
    else:
        new_form=False; err={} ; vals={}
    obs = session.query(Observation)
    itemvals = [it.name for it in item_objs]
    obs = obs.filter(or_(Observation.item.in_(itemvals),Observation.item==None))
    aspectvals = [a.name]
    obs = obs.filter(or_(Observation.aspect.in_(aspectvals),Observation.aspect==None))
    obs = obs.order_by(Observation.gravity.desc())
    obs = obs.all()

    situations = session.query(Situation).order_by(Situation.name).all() #list(set([ob.situation for ob in obs]))


    tr = {}
    for sit in situations:
        if sit.name not in tr: tr[sit.name]={}
        for it in item_objs:
            if it.name not in tr[sit.name]: tr[sit.name][it.name]={}
    for ob in obs: 
        if ob.situation_obj:
            toas = [tr[ob.situation_obj.name]]
        else:
            toas = [tr[k] for k in tr.keys()]
        for toa in toas:
            if ob.item_obj:
                toa[ob.item_obj.name][ob.id]=ob
            else:
                for k in toa:
                    toa[k][ob.id]=ob

    rsp = Response()
    if setcookie:
        for k,v in setcookie.items():
            rsp.set_cookie(k,v)
    cont = render_to_string("/observation_table.html",{'aspect':a
                                                       ,'aspects':aspects
                                                         ,'items':item_objs
                                                         ,'observations':obs
                                                         ,'situations':situations
                                                         ,'tree':tr
                                                         ,'items_str':items_str
                                                         ,'new_form':new_form
                                                         ,'new_situation':new_situation
                                                         ,'new_item':new_item
                                                         ,'gravities':gravities
                                                         ,'err':err
                                                         ,'vals':vals
                                                         ,'observation_id':observation_id
                                                       ,'obsby':obsby
                                                         ,'msg':msg},request)
    rsp.body = cont
    return rsp

def index(request):
    qry="select * from projects_iteration where project_id=%s order by cast(name as signed)"
    c = conn.cursor()
    c2 = conn.cursor(my.cursors.DictCursor)
    projectname = getprojectname(c)
    res = c.execute(qry,PROJECT_ID)
    iters = c.fetchall()
    #raise Exception('PROJECT %s iters: %s'%(PROJECT_ID,iters))
    aspects = session.query(Aspect).all()
    return render_to_response('/index.html',{'aspects':aspects,'iterations':iters,'SCRUMDO_BASEURL':SCRUMDO_BASEURL,'projectname':projectname},request)
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
