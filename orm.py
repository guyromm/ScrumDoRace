from sqlalchemy import create_engine
from sqlalchemy.orm import mapper,sessionmaker,relation
from sqlalchemy import Table, Column, LargeBinary,Float,BigInteger,Integer, String, Unicode, DateTime, Enum, MetaData, ForeignKey,Boolean
from sqlalchemy import or_,and_

from sqlalchemy import select,func

import datetime
now = datetime.datetime.now
import sqlalchemy,re,sys

echo=True
db  = create_engine('mysql://root@localhost/backlog',echo=echo)
dbs={'db':db}
meta = MetaData()

aspect_tbl = Table('aspect',meta
                 ,Column('name',Unicode(32),primary_key=True,unique=True))
item_tbl = Table('item',meta
                 ,Column('name',Unicode(32),primary_key=True,unique=True)
                 ,Column('created_at',DateTime(),default=now)
                 )
situation_tbl = Table('situation',meta
                      ,Column('name',Unicode(32),primary_key=True,unique=True)
                      ,Column('created_at',DateTime(),default=now))

gravities = ['gray','orange','red']
observation_tbl = Table('observation',meta
                        ,Column('id',Integer(),primary_key=True,unique=True)
                        ,Column('created_at',DateTime(),default=now,nullable=False)
                        ,Column('aspect',ForeignKey('aspect.name'),nullable=False)
                        ,Column('item',ForeignKey('item.name'),nullable=True)
                        ,Column('situation',ForeignKey('situation.name'),nullable=True)
                        ,Column('content',String(256),nullable=False)
                        ,Column('gravity',Enum(*gravities),nullable=False)
                        ,Column('observed_by',String(32),nullable=False)
)
class Observation(object): pass
class Aspect(object): pass
class Item(object): pass
class Situation(object): pass

mapper(Aspect,aspect_tbl)                 
mapper(Item,item_tbl)
mapper(Situation,situation_tbl)
mapper(Observation,observation_tbl,properties={'item_obj':relation(Item)
                                               ,'aspect_obj':relation(Aspect)
                                               ,'situation_obj':relation(Situation)})

Session = sessionmaker(bind=db)
session = Session()
# create tables
if __name__=='__main__':
    if 'create_all' in sys.argv:
        for dbn,db in dbs.items():
            print('creating & dropping all tables on %s'%dbn)
            if '--drop' in sys.argv:
                meta.drop_all(db)
            meta.create_all(db)


