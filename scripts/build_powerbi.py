"""Create native PBIP/PBIR reports and TMSL models from audited clean CSV tables."""
from pathlib import Path
import json,hashlib,uuid,math
import pandas as pd
from model_specs import SPECS
ROOT=Path(__file__).resolve().parents[1]
BASE='https://developer.microsoft.com/json-schemas/fabric/'

def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def literal(v):
 if isinstance(v,bool):s='true' if v else 'false'
 elif isinstance(v,(int,float)):s=str(v)+'D'
 else:s="'"+str(v).replace("'","''")+"'"
 return {'expr':{'Literal':{'Value':s}}}
def color(v):return {'solid':{'color':literal(v)}}
def field(table,name,measure=False):return {'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':name}}
def projection(table,name,measure=False):return {'field':field(table,name,measure),'queryRef':table+'.'+name,'nativeQueryRef':name,'displayName':name}
def ident(text):return hashlib.sha1(text.encode()).hexdigest()[:20]
def container(title,accent):
 return {'general':[{'properties':{'altText':literal(title)}}], 'title':[{'properties':{'show':literal(True),'text':literal(title),'fontSize':literal(12),'fontFamily':literal('Segoe UI'),'fontColor':color('#20364A'),'bold':literal(True),'titleWrap':literal(True)}}],
 'background':[{'properties':{'show':literal(True),'color':color('#FFFFFF'),'transparency':literal(0)}}],
 'border':[{'properties':{'show':literal(True),'color':color('#E1E8ED'),'radius':literal(10),'width':literal(1)}}],
 'visualHeader':[{'properties':{'show':literal(True)}}]}
def textbox(name,text,x,y,w,h,size=12,fg='#20364A',bold=False,bg=None):
 v={'$schema':BASE+'item/report/definition/visualContainer/2.4.0/schema.json','name':name,'position':{'x':x,'y':y,'z':0,'width':w,'height':h,'tabOrder':0},'visual':{'visualType':'textbox','objects':{'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':text,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'pt','color':fg,'fontWeight':'bold' if bold else 'normal'}}]}]}}]}}}
 if bg:v['visual']['visualContainerObjects']={'background':[{'properties':{'show':literal(True),'color':color(bg),'transparency':literal(0)}}]}
 return v

def infer_columns(path):
 df=pd.read_csv(path,keep_default_na=True,dtype={k:str for k in ['InvoiceKey','ProductKey','CustomerKey','CountryKey']})
 out=[]
 for c in df:
  if c=='Date':typ='dateTime'
  elif pd.api.types.is_integer_dtype(df[c]):typ='int64'
  elif pd.api.types.is_float_dtype(df[c]):typ='double'
  else:typ='string'
  out.append((c,typ))
 return out

def model(project,spec):
 p=ROOT;folder=p/'powerbi'/'Dashboard.SemanticModel';tables=[]
 keycols={(a,b) for a,b,c,d in spec['relationships']}|{(c,d) for a,b,c,d in spec['relationships']}
 ids={'InvoiceKey','CustomerKey','CountryKey','ProductKey','DateKey','SourceRow','ContactRowKey'}
 m_types={'string':'type text','int64':'Int64.Type','double':'type number','dateTime':'type date'}
 for path in sorted((p/'data/clean').glob('*.csv')):
  name=path.stem;cols=infer_columns(path);dimensions=name.startswith('Dim')
  columns=[]
  for c,t in cols:
   col={'name':c,'dataType':t,'sourceColumn':c,'summarizeBy':'none','lineageTag':str(uuid.uuid5(uuid.NAMESPACE_URL,project+'/'+name+'/'+c))}
   if c in ids and not (name=='DimCountry' and c=='CountryKey'):col['isHidden']=True
   if dimensions and (name,c) in keycols:col['isKey']=True
   if t=='dateTime':col['formatString']='dd MMM yyyy'
   if c=='YearMonth':col['sortByColumn']='YearMonthSort'
   if c=='MonthName':col['sortByColumn']='MonthNumber'
   if c=='Weekday' and 'WeekdayNumber' in dict(cols):col['sortByColumn']='WeekdayNumber'
   if c=='Month' and name=='DimMonth':col['sortByColumn']='MonthNumber'
   if c=='HourLabel':col['sortByColumn']='Hour'
   if c=='Season' and name=='DimSeason':col['sortByColumn']='SeasonOrder'
   if c=='AgeBand' and name=='DimAgeBand':col['sortByColumn']='AgeBandOrder'
   if c=='TemperatureBand':col['sortByColumn']='TemperatureBandOrder'
   if c.endswith('Order') or c.endswith('Sort'):col['isHidden']=True
   columns.append(col)
  types=', '.join('{'+json.dumps(c)+', '+m_types[t]+'}' for c,t in cols)
  expression=['let',f'    Source = Csv.Document(File.Contents(DataRoot & "{name}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),','    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),','    EmptyToNull = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),',f'    Typed = Table.TransformColumnTypes(EmptyToNull, {{{types}}}, "en-GB")','in','    Typed']
  table={'name':name,'lineageTag':str(uuid.uuid5(uuid.NAMESPACE_URL,project+'/'+name)),'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]}
  if name==spec['fact']:
   table['measures']=[{'name':n,'expression':dax,'formatString':fmt,'displayFolder':('Quality and coverage' if any(w in n for w in ['Unknown','Recorded','Coverage','Duplicate','Non-operating']) else 'Uncertainty' if ' CI ' in n else 'Performance'), 'description':n+'. Format: '+fmt+'. Definition: '+dax+'. See docs/METRIC_CONTRACT.md for denominator and interpretation limits.','lineageTag':str(uuid.uuid5(uuid.NAMESPACE_URL,project+'/measure/'+n))} for n,dax,fmt in spec['measures']]
  tables.append(table)
 relationships=[{'name':str(uuid.uuid5(uuid.NAMESPACE_URL,project+'/relationship/'+a+'/'+b)),'fromTable':a,'fromColumn':b,'toTable':c,'toColumn':d,'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection','isActive':True} for a,b,c,d in spec['relationships']]
 data_root=f'C:\\PowerBI\\{project}\\data\\clean\\'
 source=json.dumps(data_root)+' meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
 # M uses literal backslashes, not JSON/Python escape sequences.
 source='"'+data_root+'" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
 obj={'name':'Dashboard','compatibilityLevel':1567,'model':{'culture':'en-GB','sourceQueryCulture':'en-GB','defaultPowerBIDataSourceVersion':'powerBI_V3','dataAccessOptions':{'legacyRedirects':True,'returnErrorValuesAsNull':True},'expressions':[{'name':'DataRoot','kind':'m','expression':source,'description':'Absolute path to this repository data/clean folder, including trailing slash. Set before refresh.'}],'tables':tables,'relationships':relationships,'annotations':[{'name':'__PBI_TimeIntelligenceEnabled','value':'0'}]}}
 write(folder/'model.bim',obj);write(folder/'definition.pbism',{'$schema':BASE+'item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{}})
 return obj

def build(project,spec):
 p=ROOT;report=p/'powerbi'/'Dashboard.Report';definition=report/'definition';assets=report/'StaticResources'/'RegisteredResources'
 theme={'name':spec['title'],'dataColors':[spec['accent'],'#D79846','#2D5073','#71AAAE','#9C78AE','#C76876','#8EA7B5','#D5DDD9'],'background':'#F3F6F8','foreground':'#20364A','tableAccent':spec['accent'],'textClasses':{'title':{'fontFace':'Segoe UI','color':'#20364A'},'label':{'fontFace':'Segoe UI','fontSize':11,'color':'#536879'},'callout':{'fontFace':'Segoe UI','fontSize':30,'color':'#20364A'}}}
 write(assets/'Intelligence.json',theme)
 write(report/'definition.pbir',{'$schema':BASE+'item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../Dashboard.SemanticModel'}}})
 write(p/'powerbi'/'Dashboard.pbip',{'$schema':BASE+'pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'Dashboard.Report'}}],'settings':{'enableAutoRecovery':True}})
 write(definition/'report.json',{'$schema':BASE+'item/report/definition/report/2.0.0/schema.json','themeCollection':{'customTheme':{'name':'Intelligence.json','reportVersionAtImport':'5.55','type':'RegisteredResources'}},'resourcePackages':[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':'Intelligence.json','path':'Intelligence.json','type':'CustomTheme'}]}]})
 page_ids=[ident(project+'/page/'+str(i)) for i in range(3)];write(definition/'pages'/'pages.json',{'$schema':BASE+'item/report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':page_ids,'activePageName':page_ids[0]})
 inventory=[]
 for pi,(page_title,explanation,kpis,charts) in enumerate(spec['pages']):
  page_id=page_ids[pi];page_dir=definition/'pages'/page_id
  page={'$schema':BASE+'item/report/definition/page/2.0.0/schema.json','name':page_id,'displayName':f'{pi+1:02d}  {page_title}','displayOption':'FitToPage','width':1360,'height':880,'objects':{'background':[{'properties':{'color':color('#F3F6F8'),'transparency':literal(0)}}]}}
  write(page_dir/'page.json',page)
  visuals=[]
  visuals.append(textbox(ident(page_id+'header'),spec['title'],0,0,1360,64,25,fg='#FFFFFF',bold=True,bg='#132C40'))
  visuals.append(textbox(ident(page_id+'subheader'),spec['subtitle'],0,64,1360,28,11,fg='#D7E4EE',bg='#132C40'))
  visuals.append(textbox(ident(page_id+'pagecount'),f'{pi+1:02d} / 03   ·   {page_title.upper()}',968,22,365,33,10,fg='#D7E4EE',bold=True))
  visuals.append(textbox(ident(page_id+'footer'),spec['period'],30,842,1265,24,9,fg='#607486'))
  visuals.append(textbox(ident(page_id+'insight'),explanation,30,788,1298,42,11,fg=spec['accent']))
  for i,(table,col,label) in enumerate(spec['slicers']):
   name=ident(page_id+'/slicer/'+str(i));v={'$schema':BASE+'item/report/definition/visualContainer/2.4.0/schema.json','name':name,'position':{'x':30+i*438,'y':102,'z':10+i,'width':424,'height':65,'tabOrder':i+1},'visual':{'visualType':'slicer','query':{'queryState':{'Values':{'projections':[projection(table,col)]}}},'objects':{'data':[{'properties':{'mode':literal('Dropdown')}}],'selection':[{'properties':{'singleSelect':literal(False),'selectAllCheckboxEnabled':literal(True)}}],'slicerHeader':[{'properties':{'show':literal(False)}}]},'visualContainerObjects':container(label,spec['accent'])}}
   visuals.append(v)
  for i,measure in enumerate(kpis):
   name=ident(page_id+'/kpi/'+str(i));v={'$schema':BASE+'item/report/definition/visualContainer/2.4.0/schema.json','name':name,'position':{'x':30+i*329,'y':184,'z':20+i,'width':315,'height':104,'tabOrder':4+i},'visual':{'visualType':'card','query':{'queryState':{'Values':{'projections':[projection(spec['fact'],measure,True)]}}},'objects':{'labels':[{'properties':{'fontSize':literal(29),'fontFamily':literal('Segoe UI'),'color':color(spec['accent']),'labelDisplayUnits':literal(0)}}],'categoryLabels':[{'properties':{'show':literal(False)}}]},'visualContainerObjects':container(measure,spec['accent'])}}
   visuals.append(v)
  positions=[(30,306,759,229),(807,306,523,229),(30,551,759,220),(807,551,523,220)]
  for ci,(kind,title,table,category,measures,sorttable,sortcol) in enumerate(charts):
   name=ident(page_id+'/chart/'+str(ci));x,y,w,h=positions[ci]
   if kind=='tableEx':state={'Values':{'projections':[projection(table,category)]+[projection(spec['fact'],m,True) for m in measures]}}
   else:state={'Category':{'projections':[projection(table,category)]},'Y':{'projections':[projection(spec['fact'],m,True) for m in measures]}}
   query={'queryState':state}
   if sorttable:query['sortDefinition']={'sort':[{'field':field(table,category),'direction':'Ascending'}],'isDefaultSort':False}
   else:query['sortDefinition']={'sort':[{'field':field(spec['fact'],measures[0],True),'direction':'Descending'}],'isDefaultSort':False}
   if kind!='tableEx':
    tips={'retail-revenue-powerbi':['Invoice Lines','Sales Invoices'],'bank-campaign-powerbi':['Contact Records','Subscriptions','Conversion CI Lower','Conversion CI Upper'],'seoul-mobility-powerbi':['Recorded Hours','Operating Hours'] }[project]
    query['queryState']['Tooltips']={'projections':[projection(spec['fact'],m,True) for m in tips if m not in measures]}
   objects={'legend':[{'properties':{'show':literal(len(measures)>1),'fontSize':literal(9)}}]}
   if kind!='tableEx':
    objects.update({'categoryAxis':[{'properties':{'fontSize':literal(10),'showAxisTitle':literal(False)}}],'valueAxis':[{'properties':{'fontSize':literal(10),'showAxisTitle':literal(False)}}]})
   else:objects={'grid':[{'properties':{'textSize':literal(10),'rowPadding':literal(5)}}],'columnHeaders':[{'properties':{'fontColor':color('#536879'),'backColor':color('#EFF3F6'),'fontSize':literal(10)}}],'total':[{'properties':{'totals':literal(True)}}]}
   v={'$schema':BASE+'item/report/definition/visualContainer/2.4.0/schema.json','name':name,'position':{'x':x,'y':y,'z':30+ci,'width':w,'height':h,'tabOrder':8+ci},'visual':{'visualType':kind,'query':query,'objects':objects,'visualContainerObjects':container(title,spec['accent'])}}
   visuals.append(v)
  for order,v in enumerate(visuals):
   v['position']['tabOrder']=order
   v['position']['z']=order
   if v['visual']['visualType']=='textbox':
    v['visual'].setdefault('visualContainerObjects',{})['general']=[{'properties':{'altText':literal(v['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value'])}}]
   write(page_dir/'visuals'/v['name']/'visual.json',v)
  inventory.append({'name':page_title,'id':page_id,'visuals':len(visuals),'kpis':kpis,'charts':[{'type':c[0],'title':c[1]} for c in charts]})
 save={'project':project,'pages':inventory,'relationships':spec['relationships'],'measures':len(spec['measures']),'native_visuals_only':True,'source_format':'PBIP + PBIR + TMSL','desktop_validation':'Not executed; Power BI Desktop unavailable in this environment'}
 write(p/'powerbi/report_inventory.json',save)
 docs=p/'docs';docs.mkdir(exist_ok=True)
 (docs/'MEASURES.md').write_text('# Measure definitions\n\nAll measures are stored in the fact table and recalculate under active report filters.\n\n'+''.join('## '+n+'\n\n```dax\n'+dax+'\n```\n\nDisplay format: `'+fmt+'`.\n\n' for n,dax,fmt in spec['measures']))
 model(project,spec)
 print(project,'pages',len(inventory),'visuals',sum(x['visuals'] for x in inventory),flush=True)
if __name__=='__main__':
 for project,spec in SPECS.items():build(project,spec)
