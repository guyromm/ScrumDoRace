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
    if request.params.get('view_all'):
        viewitems = [i.name for i in session.query(Item).all()]
    else:
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

    #see if we have an existing story
    cur = conn.cursor()
    qry = "select id from projects_storytag where project_id=%s and name=%s"
    res = cur.execute(qry,(PROJECT_ID,'observation %s'%observation_id))
    storyobs = cur.fetchone()
    if storyobs: 
        res2 = cur.execute("select story_id from projects_storytagging where tag_id=%s",storyobs[0])
        fo = cur.fetchone()
        if fo:
            story_id = cur.fetchone()[0]
            res = cur.execute("select local_id,iteration_id from projects_story where id=%s",story_id)
            fo = cur.fetchone()
            assert fo,"could not fetch story %s for observation %s"%(story_id,storyobs)
            local_id = fo[0]
            iteration_id = fo[1]
        else:
            iteration_id = None
            story_id = None
            local_id = None
    else:
        story_id = None
        local_id = None
        iteration_id=None

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
                msg='Succesfully inserted'
                rt = Redirect('/support/%s/%s'%(a.name,items_str))
                for k,v in setcookie.items():
                    rt.set_cookie(k,v)
                return rt
            else:
                msg='Succesfully updated'
            session.commit()
            if request.params.get('create_story'):

                if (story_id==None): #can we insert
                    #find out a new local id
                    res = cur.execute("select max(local_id) from projects_story where project_id=%s",PROJECT_ID)
                    local_id = cur.fetchone()[0]+1
                    #find out the backlog iteration id
                    res = cur.execute("select id from projects_iteration where project_id=%s and default_iteration=true",PROJECT_ID)
                    iteration_id = cur.fetchone()[0]

                    insvals = {'project_id':PROJECT_ID,'summary':u'observation: %s'%o.content,'created':now(),'status':1,'local_id':local_id,'iteration_id':iteration_id}
                    qry = "insert into projects_story (%s) values (REPL)"%(",".join(insvals.keys()))
                    qry = qry.replace('REPL',','.join('%s' for val in insvals))
                    res = cur.execute(qry,insvals.values())
                    assert res==1
                    story_id = conn.insert_id()
                    res = cur.execute("insert into projects_storytag (project_id,name) values(%s,%s)",(PROJECT_ID,'observation %s'%o.id))
                    assert res==1
                    tagid = conn.insert_id()
                    res = cur.execute("insert into projects_storytagging (tag_id,story_id) values(%s,%s)",(tagid,story_id))
                    assert res==1
                    conn.commit()
                    msg ="Succesfully inserted story %s"%story_id
                    #raise Exception(story_id)
                    
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
                                                         ,'msg':msg
                                                       ,'story_id':story_id
                                                       ,'local_id':local_id
                                                       ,'iteration_id':iteration_id},request)
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
        fo = c2.fetchone()
        if fo:
            iteration_id = fo['id']
        else:
            iteration_id=None

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


def story_redir(request,story_id):
    qstr = "select id,iteration_id from projects_story where local_id=%d and project_id=%d"%(int(story_id),int(PROJECT_ID))
    c2 = conn.cursor()
    c2.execute(qstr)
    rid,itid = (c2.fetchall()[0])
    projname = getprojectname(c2)
    #http://scrum.ezscratch.com/projects/project/scratchcards/iteration/10018#story_1493
    return Redirect('%sprojects/project/%s/iteration/%s#story_%s'%(SCRUMDO_BASEURL,projname,itid,rid))
    
