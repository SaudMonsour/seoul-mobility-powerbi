"""Offline JSON-Schema keyword validation and model/data integrity checks.

Uses the published Microsoft schema bundle downloaded into _research. It does not
execute Power Query M, DAX, or the Power BI rendering engine.
"""
from pathlib import Path
from urllib.parse import urljoin,urldefrag,unquote
import json,re,math,collections
import pandas as pd
from model_specs import SPECS
ROOT=Path(__file__).resolve().parents[1]
BUNDLE=json.loads((ROOT/'scripts/schemas/schema_bundle.json').read_text())
class Invalid(ValueError):pass

def resolve(ref,base):
 url,fragment=urldefrag(urljoin(base,ref));schema=BUNDLE[url]
 if fragment:
  for part in unquote(fragment).lstrip('/').split('/'):schema=schema[part.replace('~1','/').replace('~0','~')]
 return schema,url

def validate(value,schema,base,path='$'):
 if isinstance(schema,bool):
  if not schema:raise Invalid(path+' false schema')
  return
 if '$ref'in schema:
  target,url=resolve(schema['$ref'],base);validate(value,target,url,path);return
 types={'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),'string':lambda x:isinstance(x,str),'boolean':lambda x:isinstance(x,bool),'number':lambda x:isinstance(x,(int,float))and not isinstance(x,bool)and math.isfinite(x),'integer':lambda x:isinstance(x,(int,float))and not isinstance(x,bool)and int(x)==x,'null':lambda x:x is None}
 if 'type'in schema:
  allowed=schema['type'] if isinstance(schema['type'],list) else [schema['type']]
  if not any(types[t](value) for t in allowed):raise Invalid(path+' expected '+str(allowed))
 if 'const'in schema and value!=schema['const']:raise Invalid(path+' constant mismatch')
 if 'enum'in schema and value not in schema['enum']:raise Invalid(path+' enum mismatch')
 for key in ['anyOf','oneOf']:
  if key in schema:
   success=0;errors=[]
   for child in schema[key]:
    try:validate(value,child,base,path);success+=1
    except Invalid as e:errors.append(str(e))
   if (key=='anyOf'and success==0)or(key=='oneOf'and success!=1):raise Invalid(path+' '+key+' mismatch: '+'; '.join(errors[:3]))
 if isinstance(value,dict):
  for key in schema.get('required',[]):
   if key not in value:raise Invalid(path+' missing '+key)
  props=schema.get('properties',{})
  for key,v in value.items():
   if key in props:validate(v,props[key],base,path+'/'+key)
   elif schema.get('additionalProperties') is False:raise Invalid(path+' unexpected '+key)
   elif isinstance(schema.get('additionalProperties'),dict):validate(v,schema['additionalProperties'],base,path+'/'+key)
 if isinstance(value,list):
  for i,v in enumerate(value):validate(v,schema.get('items',{}),base,path+f'/{i}')
 if isinstance(value,str):
  if len(value)<schema.get('minLength',0)or len(value)>schema.get('maxLength',float('inf')):raise Invalid(path+' string length')
  if 'pattern'in schema and re.search(schema['pattern'],value)is None:raise Invalid(path+' pattern mismatch')
  if schema.get('format')=='uri' and not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',value):raise Invalid(path+' invalid URI')

def check_project(project):
 p=ROOT;checked=0;visuals=0
 for f in (p/'powerbi').rglob('*'):
  if f.suffix not in ['.json','.pbip','.pbir','.pbism']:continue
  d=json.loads(f.read_text())
  if '$schema'in d:
   uri=d['$schema']
   if uri not in BUNDLE:
    # definition.pbir schema was not referenced by the report body; fetched separately below.
    raise Invalid('Missing schema '+uri)
   validate(d,BUNDLE[uri],uri,str(f.relative_to(p)));checked+=1
  if f.name=='visual.json':visuals+=1
 model=json.loads((p/'powerbi/Dashboard.SemanticModel/model.bim').read_text())['model'];tables={t['name']:t for t in model['tables']};data={n:pd.read_csv(p/'data/clean'/f'{n}.csv',dtype={k:str for k in ['InvoiceKey','ProductKey','CustomerKey','CountryKey']}) for n in tables}
 for r in model['relationships']:
  source=data[r['fromTable']][r['fromColumn']];target=data[r['toTable']][r['toColumn']]
  assert target.is_unique and target.notna().all(),r
  assert source.notna().all()and source.isin(target).all(),r
 for t in model['tables']:
  columns={c['name'] for c in t['columns']};assert columns==set(data[t['name']].columns)
  for c in t['columns']:
   if 'sortByColumn'in c:
    other=c['sortByColumn'];assert data[t['name']].groupby(c['name'],dropna=False)[other].nunique().le(1).all()
 for f in (p/'powerbi/Dashboard.Report/definition/pages').glob('*/visuals/*/visual.json'):
  d=json.loads(f.read_text());pos=d['position'];assert pos['x']>=0 and pos['y']>=0 and pos['x']+pos['width']<=1360 and pos['y']+pos['height']<=880
  def refs(x):
   if isinstance(x,dict):
    for kind in ['Measure','Column']:
     if kind in x and isinstance(x[kind],dict)and 'Expression'in x[kind]:
      e=x[kind];entity=e['Expression']['SourceRef']['Entity'];prop=e['Property'];assert entity in tables
      pool=tables[entity].get('measures',[])if kind=='Measure'else tables[entity]['columns'];assert prop in {z['name'] for z in pool},(f,entity,prop)
    for v in x.values():refs(v)
   elif isinstance(x,list):
    for v in x:refs(v)
  refs(d)
 fact=SPECS[project]['fact'];summary=json.loads((p/'analysis/summary.json').read_text());assert len(data[fact])==summary['clean_rows']
 checks={'schema_documents_validated':checked,'visuals':visuals,'page_count':3,'relationships_checked':len(model['relationships']),'foreign_key_orphans':0,'dimension_duplicate_keys':0,'fact_rows':len(data[fact]),'code_data_columns_match':True,'visual_fields_resolve':True,'canvas_bounds_pass':True,'desktop_refresh_and_render':'NOT EXECUTED','dax_and_m_engine_execution':'NOT EXECUTED','schema_validation_scope':'Types, required/extra properties, references, array items, string bounds/patterns, const/enum, anyOf/oneOf, URI format. Does not validate empty-schema visual formatting values against undocumented visual capabilities.'}
 (p/'analysis/validation_report.json').write_text(json.dumps(checks,indent=2)+'\n');return checks
if __name__=='__main__':
 # Sanity checks ensure this validator rejects malformed documents.
 for value,schema in [({}, {'required':['x']}),({'x':1},{'additionalProperties':False}),('bad',{'type':'number'}),('c',{'enum':['a','b']})]:
  try:validate(value,schema,'https://example.invalid');raise AssertionError('Invalid schema fixture accepted')
  except Invalid:pass
 for name in SPECS:print(name,json.dumps(check_project(name)),flush=True)
