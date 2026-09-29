import argparse, copy, importlib.util, json, shutil, subprocess, sys, tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('project', type=Path)
args = parser.parse_args()
PROJECT = args.project.resolve()
SRC = PROJECT / 'skill/aix-style-library'
spec = importlib.util.spec_from_file_location('aix_review', SRC / 'scripts/aix.py')
aix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aix)
results = []
def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def call(root, argv):
    obj, code = aix.run(argv, root=root)
    return {'exit_code':code, 'code':obj['code'], 'data':obj['data']}
def record(name, observed, expected):
    results.append({'probe':name,'observed':observed,'expected':expected})
def clone(base):
    root=base/'skill'
    evidence=base/'evidence'
    shutil.copytree(SRC,root)
    shutil.copytree(PROJECT/'evaluation',evidence)
    return root,evidence

def probe(name, fn):
    with tempfile.TemporaryDirectory(prefix='aix-review-') as temp:
        base=Path(temp); root,evidence=clone(base)
        try:fn(base,root,evidence)
        except Exception as exc:record(name,{'exception':repr(exc)},'No uncaught exception')

probe('baseline_release', lambda b,r,e: record('baseline_release',call(r,['validate','--scope','release','--evidence-root',str(e)]),'preview only, not formal certification'))

def file_links(b,r,e):
    for filename in ('style.json','thumbnail.webp'):
        path=r/'styles/Aix0001'/filename
        outside=b/('outside-'+filename)
        original=path.read_bytes(); outside.write_bytes(original)
        path.unlink(); path.symlink_to(outside)
        result=call(r,['get','--id','0001'])
        record('external_file_symlink_'+filename,{'code':result['code'],'exit_code':result['exit_code']},'PATH_OUTSIDE_LIBRARY')
        path.unlink();path.write_bytes(original)
    directory=r/'styles/Aix0001'; outside=b/'outside-style'
    directory.rename(outside);directory.symlink_to(outside,target_is_directory=True)
    result=call(r,['get','--id','0001'])
    record('external_directory_symlink',{'code':result['code']},'PATH_OUTSIDE_LIBRARY')
probe('file_links', file_links)

def bad_thumb(b,r,e):
    (r/'styles/Aix0001/thumbnail.webp').write_bytes(b'this is not an image')
    call(r,['build-index'])
    record('nonimage_thumbnail_release',call(r,['validate','--scope','release','--evidence-root',str(e)]),'reject invalid image')
probe('bad_thumb',bad_thumb)

def low_scores(b,r,e):
    path=e/'results/0.1.0/Aix0001.json';obj=read(path)
    sample=copy.deepcopy(obj['samples'][0]);sample['style_score']=sample['content_score']=1
    obj['samples']=[copy.deepcopy(sample) for _ in range(6)];obj['versatility_score']=1
    write(path,obj)
    record('six_duplicate_one_point_samples_release',call(r,['validate','--scope','release','--evidence-root',str(e)]),'reject duplicate samples / absent subject coverage / below threshold')
probe('low_scores',low_scores)

def empty_index(b,r,e):
    path=r/'catalog/index.json';obj=read(path);obj['styles']=[];write(path,obj)
    record('empty_index_with_original_digest_release',call(r,['validate','--scope','release','--evidence-root',str(e)]),'INDEX_STALE')
    request=b/'request.json';write(request,{'api_version':'1.0','operation':'search','query':'水彩','terms':['水彩'],'category':None,'limit':3})
    record('search_after_empty_index_release',call(r,['search','--input',str(request)]),'reject invalid index, not silent empty result')
probe('empty_index',empty_index)

def bad_library(b,r,e):
    write(r/'library.json',[])
    completed=subprocess.run([sys.executable,str(r/'scripts/aix.py'),'get','--id','0001'],capture_output=True,text=True)
    record('nonobject_library_json',{'exit_code':completed.returncode,'stdout':completed.stdout,'stderr_has_traceback':'Traceback' in completed.stderr},'single JSON error envelope, no traceback')
probe('bad_library',bad_library)

def formal_version(b,r,e):
    obj=read(r/'library.json');obj['library_version']='1.0.0';write(r/'library.json',obj);call(r,['build-index'])
    record('three_procedural_styles_as_1_0_0_release',call(r,['validate','--scope','release','--evidence-root',str(e)]),'formal acceptance not satisfied')
probe('formal_version',formal_version)

def missing_key(b,r,e):
    path=r/'styles/Aix0001/style.json';obj=read(path);obj.pop('replacement_id');write(path,obj)
    out=call(r,['get','--id','0001'])
    schema=read(r/'references/schemas/style.schema.json')
    record('schema_required_replacement_id_missing',{'code':out['code'],'schema_requires_key':'replacement_id' in schema['required']},'STYLE_INVALID')
probe('missing_key',missing_key)

def search_terms(b,r,e):
    for term in ['水彩','儿童绘本','奶油色系']:
        request=b/'request.json';write(request,{'api_version':'1.0','operation':'search','query':term,'terms':[term],'category':None,'limit':3})
        out=call(r,['search','--input',str(request)])
        record('search_'+term,{'code':out['code'],'ids':[c['id'] for c in out['data']['candidates']]},'known fitting style Aix0002; suitability/description-only terms are currently below threshold')
probe('search_terms',search_terms)

probe('coffee_prompt',lambda b,r,e: record('coffee_prompt',call(r,['prepare','--input',str(PROJECT/'tests/fixtures/requests/prepare-coffee.json')]),'review final prompt for human skin / skin tone leakage into product task'))

def package_preview(b,r,e):
    spec=importlib.util.spec_from_file_location('build_review',PROJECT/'tools/build_release.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    builder.SKILL_DIR=r;builder.RELEASES=b/'releases'
    obj=read(r/'styles/Aix0003/style.json');obj['status']='draft';write(r/'styles/Aix0003/style.json',obj)
    call(r,['build-index']);(r/'private-request.json').write_text('{"example":"synthetic local prompt"}')
    import zipfile
    path=builder.build('9.9.9')
    with zipfile.ZipFile(path) as archive:
        record('release_archive_scope',{'includes_draft':any('styles/Aix0003/' in n for n in archive.namelist()),'includes_extra_request':'aix-style-library/private-request.json' in archive.namelist(),'filename_version':'9.9.9','internal_version':json.loads(archive.read('aix-style-library/library.json'))['library_version']},'exclude drafts/temp requests; package version matches library version')
probe('package_preview',package_preview)
print(json.dumps(results,ensure_ascii=False,indent=2))
