"""Regression tests for release, path, index, error and archive invariants.

Run with requirements-dev.txt installed. All mutations use temporary copies.
Formal evidence fixtures are synthetic test data, never publishable evidence.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import jsonschema
from PIL import Image
from test_aix import PROJECT, SKILL_SRC, aix, base_prepare, read_json, write_json, write_request


class ReliabilityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aix reliability 测试 ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "skill"
        self.evidence = self.base / "evaluation"
        shutil.copytree(SKILL_SRC, self.root)
        shutil.copytree(PROJECT / "evaluation" / "rights", self.evidence / "rights")
        self.make_complete_evidence()
        self.response_schema = read_json(SKILL_SRC / "references/schemas/response.schema.json")

    def make_complete_evidence(self):
        """为克隆库生成结构完整的合成证据夹具（每风格 6 样本、三类主体各 2 张）。

        这些是用于验证发布校验机制的合成数据，不是可发布证据，也与仓库中
        真实的 0.2.0 内容样张相互独立（对应本文件开头“合成夹具”的说明）。
        """
        for style_dir in sorted(p for p in (self.root / "styles").iterdir() if p.is_dir()):
            obj = read_json(style_dir / "style.json")
            sid = obj["id"]
            record_path = self.evidence / obj["quality"]["evidence_ref"]
            record_path.parent.mkdir(parents=True, exist_ok=True)
            results_dir = Path(obj["quality"]["evidence_ref"]).parent.as_posix()
            samples = []
            number = int(sid[-4:])
            for index in range(6):
                rel = "%s/images/%s-%02d.png" % (results_dir, sid, index + 1)
                image_path = self.evidence / rel
                image_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (64, 64), (number, index * 40, 0)).save(image_path)
                samples.append({
                    "case_id": "%s-%02d" % (sid, index + 1),
                    "subject_category": ["人物", "人物", "物体", "物体", "场景", "场景"][index],
                    "prompt": "synthetic fixture sample %s-%02d" % (sid, index + 1),
                    "image_path": rel,
                    "style_score": 5,
                    "content_score": 5,
                    "notes": "synthetic validation fixture, not publishable evidence",
                })
            write_json(record_path, {
                "style_id": sid,
                "style_version": obj["version"],
                "tested_tool": obj["quality"]["tested_tool"],
                "tested_at": obj["quality"]["tested_at"],
                "reviewer": "synthetic fixture (tests)",
                "review_mode": "self_blind",
                "evidence_type": "image_model",
                "rights_record": "rights/%s.md" % sid,
                "samples": samples,
                "versatility_score": 5,
                "limitations": "synthetic test fixture, not publishable evidence",
            })

    def record_path(self, sid="Aix0001"):
        style = read_json(self.root / "styles" / sid / "style.json")
        return self.evidence / style["quality"]["evidence_ref"]

    def run_cli(self, *args):
        output, code = aix.run(list(args), root=self.root)
        jsonschema.Draft202012Validator(self.response_schema).validate(output)
        return output, code

    def release(self):
        return self.run_cli("validate", "--scope", "release", "--evidence-root", str(self.evidence))

    def assertRejected(self, result, expected=None):
        output, code = result
        self.assertNotEqual(code, 0, output)
        self.assertEqual(output["status"], "error")
        if expected:
            self.assertEqual(output["code"], expected, output)

    def change_record(self, edit, sid="Aix0001"):
        style = read_json(self.root / "styles" / sid / "style.json")
        path = self.evidence / style["quality"]["evidence_ref"]
        obj = read_json(path)
        edit(obj)
        write_json(path, obj)

    def test_preview_release_is_explicit_and_read_only(self):
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        output, code = self.release()
        self.assertEqual(code, 0, output)
        self.assertEqual(output['data']['release_profile'], 'preview')
        self.assertFalse(output['data']['formal_evidence_checked'])
        self.assertEqual(output['warnings'][0]['code'], 'PREVIEW_ONLY')
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_bad_metadata_returns_one_json_without_traceback(self):
        path = self.root / 'library.json'
        original = read_json(path)
        variants = [[], None, {}, {**original, 'library_version':'../x'}, {**original, 'schema_version':'9'},
                    {**original, 'api_version':'9'}]
        for value in variants:
            with self.subTest(value=value):
                write_json(path, value)
                result = subprocess.run([sys.executable, '-B', str(self.root/'scripts/aix.py'), 'get', '--id', '1'],
                                        capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 4)
                output = json.loads(result.stdout)
                jsonschema.validate(output, self.response_schema)
                self.assertEqual(output['code'], 'SCHEMA_UNSUPPORTED')
                self.assertEqual(result.stderr, '')
        path.unlink()
        self.assertRejected(self.run_cli('get','--id','1'), 'SCHEMA_UNSUPPORTED')

    def test_unknown_missing_and_duplicate_cli_options(self):
        for args in [[], ['nonsense'], ['get','--id'], ['get','--id','1','--id','2']]:
            self.assertRejected(self.run_cli(*args), 'INVALID_REQUEST')

    def test_runtime_is_utf8_with_no_site_packages_and_legacy_stdio(self):
        request = write_request(self.base, base_prepare())
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        for args in [['get', '--id', '1'], ['prepare', '--input', str(request)]]:
            result = subprocess.run(
                [sys.executable, '-B', '-S', str(self.root/'scripts/aix.py'), *args],
                env={**os.environ, 'PYTHONIOENCODING': 'ascii'}, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout.decode('utf-8'))
            jsonschema.validate(output, self.response_schema)
            self.assertEqual(result.stderr, b'')
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_malformed_requests_are_protocol_errors(self):
        path = self.base/'request.json'
        for value in [b'[]', b'null', b'{', b'\xff', b'{"description":"\\ud800"}', b'['*2000+b']'*2000]:
            with self.subTest(value=value[:30]):
                path.write_bytes(value)
                self.assertRejected(self.run_cli('prepare','--input',str(path)), 'INVALID_REQUEST')

    def test_missing_required_nullable_fields_are_rejected(self):
        path=self.root/'styles/Aix0001/style.json';original=read_json(path)
        for parent,key in [(None,'replacement_id'),('quality','tested_tool'),('provenance','attribution')]:
            with self.subTest(parent=parent,key=key):
                obj=copy.deepcopy(original)
                (obj if parent is None else obj[parent]).pop(key)
                write_json(path,obj)
                self.assertRejected(self.run_cli('get','--id','1'))
        for parent,key in [(None,'style_version'),('intent','aspect_ratio')]:
            req=base_prepare();(req if parent is None else req[parent]).pop(key)
            request=write_request(self.base,req)
            self.assertRejected(self.run_cli('prepare','--input',str(request)), 'INVALID_REQUEST')

    def test_invalid_date_and_empty_active_references(self):
        path=self.root/'styles/Aix0001/style.json';original=read_json(path)
        for parent,key,value in [('quality','tested_at','2026-02-30'),('quality','tested_tool','  '),('provenance','source_ref','')]:
            obj=copy.deepcopy(original);obj[parent][key]=value;write_json(path,obj)
            self.assertRejected(self.run_cli('get','--id','1'))

    def test_external_file_symlinks_rejected_internal_links_allowed(self):
        for relative in ['styles/Aix0001/style.json','styles/Aix0001/thumbnail.webp','library.json','catalog/index.json']:
            with self.subTest(relative=relative):
                path=self.root/relative;original=path.read_bytes();outside=self.base/('outside-'+path.name)
                outside.write_bytes(original);path.unlink();path.symlink_to(outside)
                args=('validate','--scope','all') if relative.startswith('catalog') else ('get','--id','1')
                self.assertRejected(self.run_cli(*args), 'PATH_OUTSIDE_LIBRARY')
                path.unlink();path.write_bytes(original)
        thumb=self.root/'styles/Aix0001/thumbnail.webp'
        internal=self.root/'internal.webp';thumb.rename(internal);thumb.symlink_to(internal)
        self.assertEqual(self.run_cli('get','--id','1')[1],0)

    def test_evidence_paths_reject_escape_and_absolute_paths(self):
        path=self.record_path('Aix0001');original=read_json(path)
        for reference in ['../outside.json',str(self.base/'outside.json'),'results\\outside.json']:
            obj=copy.deepcopy(original);obj['rights_record']=reference;write_json(path,obj)
            self.assertRejected(self.release())
        write_json(path,original)
        rights=self.evidence/'rights/Aix0001.md';outside=self.base/'rights.md';rights.rename(outside);rights.symlink_to(outside)
        self.assertRejected(self.release())

    def test_index_tampering_and_malformed_records_rejected(self):
        path=self.root/'catalog/index.json';original=read_json(path)
        mutations=[lambda x:x.update(styles=[]),lambda x:x['styles'][0].update(name='篡改名称'),
                   lambda x:x['styles'].append(copy.deepcopy(x['styles'][0])),lambda x:x.update(styles={}),
                   lambda x:x.update(library_version='9.0.0'),lambda x:x['styles'][0].update(id='../outside')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                obj=copy.deepcopy(original);mutate(obj);write_json(path,obj)
                self.assertRejected(self.run_cli('validate','--scope','all'), 'INDEX_STALE')
        obj=copy.deepcopy(original);obj['styles']=[];obj['source_digest']=aix.source_digest([]);write_json(path,obj)
        request=write_request(self.base,{'api_version':'1.0','operation':'search','query':'水彩','terms':['水彩'],'category':None,'limit':3})
        self.assertRejected(self.run_cli('search','--input',str(request)), 'INDEX_STALE')
        for value in [[],None,{'schema_version':'1.0'}]:
            write_json(path,value)
            self.assertRejected(self.run_cli('search','--input',str(request)), 'INDEX_STALE')

    def test_search_checks_selected_entry_fields(self):
        path=self.root/'catalog/index.json';index=read_json(path)
        index['styles'][0]['name']='伪造的检索名';write_json(path,index)
        request=write_request(self.base,{'api_version':'1.0','operation':'search','query':'伪造的检索名','terms':['伪造的检索名'],'category':None,'limit':3})
        self.assertRejected(self.run_cli('search','--input',str(request)), 'INDEX_STALE')

    def test_corrupt_and_wrong_dimension_thumbnail_rejected(self):
        path=self.root/'styles/Aix0001/thumbnail.webp'
        for kind in ['text','png','small','oversize']:
            with self.subTest(kind=kind):
                if kind=='text':path.write_text('not an image')
                elif kind=='png':Image.new('RGB',(640,400)).save(path,format='PNG')
                elif kind=='small':Image.new('RGB',(320,200)).save(path,format='WEBP')
                else:path.write_bytes(b'x'*(aix.THUMB_LIMIT_BYTES+1))
                self.run_cli('build-index')
                self.assertRejected(self.release())

    def test_duplicate_sample_id_path_and_pixels_rejected(self):
        path=self.record_path('Aix0001');original=read_json(path)
        for field in ['case_id','image_path']:
            obj=copy.deepcopy(original);obj['samples'][1][field]=obj['samples'][0][field];write_json(path,obj)
            self.assertRejected(self.release())
        write_json(path,original)
        first=self.evidence/original['samples'][0]['image_path'];second=self.evidence/original['samples'][1]['image_path']
        with Image.open(first) as image:image.save(second,format='PNG',compress_level=1)
        self.assertRejected(self.release())

    def test_invalid_samples_and_low_scores_rejected(self):
        path=self.record_path('Aix0001');original=read_json(path)
        variants=[]
        obj=copy.deepcopy(original)
        for sample in obj['samples']:sample['subject_category']='人物'
        variants.append(obj)
        for field,value in [('style_score',1),('content_score',1),('style_score',True)]:
            obj=copy.deepcopy(original)
            for sample in obj['samples']:sample[field]=value
            variants.append(obj)
        obj=copy.deepcopy(original);obj['versatility_score']=1;variants.append(obj)
        obj=copy.deepcopy(original);obj['tested_tool']='another tool';variants.append(obj)
        obj=copy.deepcopy(original);obj['samples']=None;variants.append(obj)
        for obj in variants:
            write_json(path,obj);self.assertRejected(self.release())

    def test_global_content_threshold_rejected_despite_style_average(self):
        # 全库内容分达标率 <95% 必须被拒绝，即使每个受影响风格的均分仍 ≥4。
        # 低分样本数量随库规模变化：在前 k 个风格各取 1 个样本记 3 分，
        # 使 (total-k)/total < 0.95，同时每个受影响风格均分 = (5×5+3)/6 ≈ 4.67。
        style_ids = sorted(p.name for p in (self.root / "styles").iterdir() if p.is_dir())
        k = (len(style_ids) * 6) // 20 + 1
        for sid in style_ids[:k]:
            def change(obj):
                for sample in obj['samples']:sample['content_score']=5
                obj['samples'][0]['content_score']=3
            self.change_record(change, sid=sid)
        self.assertRejected(self.release())

    def test_release_rejects_insufficient_samples(self):
        # 正式门槛负例：每风格至少 6 个样本，少一个都必须被拒绝。
        path=self.record_path('Aix0001');record=read_json(path)
        record['samples']=record['samples'][:5]
        write_json(path,record)
        self.assertRejected(self.release(), 'STYLE_INVALID')

    def test_sample_image_must_decode(self):
        record=read_json(self.record_path('Aix0001'))
        (self.evidence/record['samples'][0]['image_path']).write_text('not an image')
        self.assertRejected(self.release(), 'ASSET_MISSING')

    def test_missing_dependencies_fail_without_installing(self):
        real_import=__import__
        def guarded(name,*args,**kwargs):
            if name in ('jsonschema','PIL'):raise ImportError('test dependency unavailable')
            return real_import(name,*args,**kwargs)
        with mock.patch('builtins.__import__',side_effect=guarded):
            output,code=aix.run(['validate','--scope','release','--evidence-root',str(self.evidence)],root=self.root)
        self.assertEqual(code,4);self.assertEqual(output['code'],'DEPENDENCY_MISSING')

    def test_declaring_formal_version_cannot_bypass_gate(self):
        # 库规模不足时声明正式档必须以 RELEASE_NOT_READY 拒绝；
        # 先收缩到 5 个风格，使该门槛与真实库规模（可能已达 20）无关地生效。
        style_dirs=sorted(p for p in (self.root/'styles').iterdir() if p.is_dir())
        for style_dir in style_dirs[5:]:
            shutil.rmtree(style_dir)
        path=self.root/'library.json';obj=read_json(path);obj['library_version']='1.0.0';write_json(path,obj)
        self.run_cli('build-index')
        self.assertRejected(self.release(), 'RELEASE_NOT_READY')

    def test_baseline_blocks_same_version_rewrites_and_missing_published_ids(self):
        old=self.base/'baseline';shutil.copytree(self.root,old)
        path=self.root/'styles/Aix0001/style.json';obj=read_json(path);obj['description']='改动内容';write_json(path,obj)
        self.run_cli('build-index')
        self.assertRejected(self.run_cli('validate','--scope','release','--evidence-root',str(self.evidence),'--baseline',str(old)))
        shutil.rmtree(self.root/'styles/Aix0001');self.run_cli('build-index')
        self.assertRejected(self.run_cli('validate','--scope','release','--evidence-root',str(self.evidence),'--baseline',str(old)))

    def test_response_schema_rejects_missing_success_fields(self):
        output,code=self.run_cli('get','--id','1');self.assertEqual(code,0)
        del output['data']['provenance']
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(output,self.response_schema)
        output['status']='error'
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(output,self.response_schema)

    def load_builder(self):
        spec=importlib.util.spec_from_file_location('builder_test',PROJECT/'tools/build_release.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        builder.SKILL_DIR=self.root;builder.RELEASES=self.base/'releases';builder.EVIDENCE=self.evidence
        return builder

    def test_archive_excludes_drafts_and_extras_and_matches_index(self):
        builder=self.load_builder()
        # 使用高位空闲编号做夹具，避免与真实风格 ID 冲突。
        for sid,status in [('Aix9001','draft'),('Aix9002','deprecated')]:
            directory=self.root/'styles'/sid;directory.mkdir()
            obj=read_json(self.root/'styles/Aix0001/style.json');obj['id']=sid;obj['status']=status
            if status=='deprecated':obj['replacement_id']='Aix0001'
            write_json(directory/'style.json',obj)
            if status!='draft':shutil.copyfile(self.root/'styles/Aix0001/thumbnail.webp',directory/'thumbnail.webp')
        (self.root/'private-request.json').write_text('{"prompt":"test"}')
        (self.root/'styles/Aix0001/notes.txt').write_text('not runtime')
        archive=builder.build()
        with zipfile.ZipFile(archive) as z:
            names=z.namelist();self.assertFalse(any('Aix9001' in n or 'private-request' in n or 'notes.txt' in n or '.DS_Store' in n for n in names))
            self.assertIn('aix-style-library/styles/Aix9002/style.json',names)
            index=json.loads(z.read('aix-style-library/catalog/index.json'))
            # 仅遍历目录条目（非目录如 .DS_Store 不参与索引期望）。
            expected=sorted(read_json(d/'style.json')['id'] for d in (self.root/'styles').iterdir()
                            if d.is_dir() and read_json(d/'style.json')['status']!='draft')
            self.assertEqual([e['id'] for e in index['styles']],expected)
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(archive.with_suffix('.zip.sha256').read_text().split()[0],digest)
        with self.assertRaises(ValueError):builder.build()
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),digest)
        builder.RELEASES=self.base/'releases-two'
        self.assertEqual(builder.build().read_bytes(),archive.read_bytes())

    def test_archive_rejects_version_mismatch_and_failed_validation_leaves_no_zip(self):
        builder=self.load_builder()
        with self.assertRaises(ValueError):builder.build('9.9.9')
        (self.root/'styles/Aix0001/thumbnail.webp').write_text('bad image')
        with self.assertRaises(ValueError):builder.build()
        self.assertEqual(list(builder.RELEASES.glob('*.zip')),[])
        self.assertEqual(list(builder.RELEASES.glob('*.sha256')),[])
        self.assertEqual(list(builder.RELEASES.glob('.aix-stage-*')),[])

    def test_archive_validation_failure_never_replaces_existing_zip(self):
        builder=self.load_builder();builder.RELEASES.mkdir()
        target=builder.RELEASES/('aix-style-library-%s.zip'%aix.library_version(self.root))
        target.write_bytes(b'existing published bytes')
        with self.assertRaises(ValueError):builder.build()
        self.assertEqual(target.read_bytes(),b'existing published bytes')

    def make_formal_fixture(self):
        """Generate explicitly synthetic fixtures to test formal gate mechanics."""
        version='1.0.0';write_json(self.root/'library.json',{'library_version':version,'schema_version':'1.0','api_version':'1.0'})
        template=read_json(self.root/'styles/Aix0001/style.json')
        thumb=(self.root/'styles/Aix0001/thumbnail.webp').read_bytes()
        shutil.rmtree(self.root/'styles');(self.root/'styles').mkdir()
        for number in range(1,21):
            sid='Aix%04d'%number;directory=self.root/'styles'/sid;directory.mkdir()
            obj=copy.deepcopy(template);obj['id']=sid;obj['category']=['graphic','illustration','photographic'][number%3]
            obj['quality'].update(tested_tool='SYNTHETIC TEST ONLY',evidence_ref='results/1.0.0/%s.json'%sid)
            write_json(directory/'style.json',obj);(directory/'thumbnail.webp').write_bytes(thumb)
            record={'style_id':sid,'style_version':obj['version'],'tested_tool':'SYNTHETIC TEST ONLY','tested_at':obj['quality']['tested_at'],'reviewer':'SYNTHETIC TEST ONLY','review_mode':'independent','rights_record':'rights/Aix0001.md','samples':[],'versatility_score':5,'evidence_type':'image_model'}
            for index in range(6):
                image_ref='results/1.0.0/%s-%d.png'%(sid,index);path=self.evidence/image_ref;path.parent.mkdir(parents=True,exist_ok=True)
                Image.new('RGB',(16,16),(number,index*40,0)).save(path)
                generation_ref='results/1.0.0/%s-%d-call.json'%(sid,index)
                prompt='Synthetic subject %s %d'%(sid,index)
                write_json(self.evidence/generation_ref,{'status':'generated','tool':'SYNTHETIC TEST ONLY','prompt':prompt,'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'parameters':{}})
                record['samples'].append({'case_id':'%s-%d'%(sid,index),'subject_category':['人物','物体','场景'][index//2],'prompt':prompt,'image_path':image_ref,'style_score':5,'content_score':5,'notes':'Synthetic validator fixture','generation_ref':generation_ref})
            write_json(self.evidence/obj['quality']['evidence_ref'],record)
        self.run_cli('build-index')
        gates={}
        for name in ['agent_behavior','search','host_tool','portability','rollback']:
            ref='results/1.0.0/%s.md'%name;path=self.evidence/ref;path.write_text('SYNTHETIC TEST ATTESTATION, NOT ACTUAL ACCEPTANCE')
            gates[name]={'status':'passed','record_ref':ref,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        write_json(self.evidence/'results/1.0.0/acceptance.json',{'library_version':version,'source_digest':read_json(self.root/'catalog/index.json')['source_digest'],'reviewer':'SYNTHETIC TEST ONLY','gates':gates})

    def test_formal_gates_require_bound_generation_and_acceptance_evidence(self):
        self.make_formal_fixture()
        output,code=self.release();self.assertEqual(code,0,output);self.assertTrue(output['data']['formal_evidence_checked'])
        record_path=self.evidence/'results/1.0.0/Aix0001.json';record=read_json(record_path)
        record.pop('evidence_type');write_json(record_path,record)
        self.assertRejected(self.release(),'RELEASE_NOT_READY')
        record['evidence_type']='image_model';write_json(record_path,record)
        gen=self.evidence/record['samples'][0]['generation_ref'];original=read_json(gen)
        for key,value in [('status','queued'),('image_sha256','0'*64),('prompt','wrong prompt')]:
            obj=copy.deepcopy(original);obj[key]=value;write_json(gen,obj)
            self.assertRejected(self.release(),'RELEASE_NOT_READY')
        write_json(gen,original)
        acceptance=self.evidence/'results/1.0.0/acceptance.json';original=read_json(acceptance)
        for edit in [lambda x:x.update(source_digest='0'*64),lambda x:x['gates']['agent_behavior'].update(status='failed'),lambda x:x['gates']['rollback'].update(sha256='0'*64)]:
            obj=copy.deepcopy(original);edit(obj);write_json(acceptance,obj)
            self.assertRejected(self.release(),'RELEASE_NOT_READY')
        acceptance.unlink();self.assertRejected(self.release())


if __name__=='__main__':unittest.main()
