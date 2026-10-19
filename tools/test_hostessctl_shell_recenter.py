"""Production caller with a real neutral child; never device acceptance."""
import argparse
from copy import deepcopy
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.hostessctl import companion_shell_recenter as recenter
from tools.hostessctl.companion_report_projection import build_companion_report_projection, utc_now
from tools.hostessctl.companion_catalog import build_companion_catalog_report


PEER = r'''
import json, pathlib, sys, time
mode = sys.argv[1]
assert sys.argv[2] == '--request'
request = json.loads(pathlib.Path(sys.argv[3]).read_bytes())
root = pathlib.Path(request['output_dir'])
if mode == 'reconcile':
    print((root / ('RESULT.json' if (root / 'RESULT.json').exists() else 'STATUS.json')).read_text())
    sys.exit(0)
root.mkdir()
(root / 'calls').write_text(mode)
assert root.with_name(root.name + '.hostess-intent.json').exists()
assert root.with_name(root.name + '.hostess-request.json').exists()
if request['operator_id'] == 'exit-without-result':
    sys.exit(3)
result = {'schema':'rusty.quest.shell_recenter.result.v1',
    **{k:request[k] for k in ('request_id','nonce','boot_id','artifact')},
    'source_id':request['source']['source_id'],
    'request_sha256':__import__('hashlib').sha256((json.dumps(request,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest(),
    'availability':{'status':'ready','reason':'neutral peer only','privilege':'android_shell_uid_2000'},
    'dispatch':{'state':'not_sent' if mode == 'readiness' else 'sent'},
    'callback':{'state':'not_received' if mode == 'readiness' else 'success'},
    'effect':{'state':'unverified'}, 'original':{'state':'retired','retired':True},
    'cleanup':{'state':'complete'}}
if request['operator_id'] == 'unavailable':
    result['availability']['status'] = 'unavailable'
    result['dispatch']['state'] = 'not_sent'
    result['callback']['state'] = 'not_received'
elif request['operator_id'] == 'late-error':
    result['callback'] = {'state':'error','error':{'code':7,'message':'original error'}}
elif request['operator_id'] == 'pending':
    result['callback']['state'] = 'not_received'
    result['original'] = {'state':'active','retired':False}
    result['cleanup']['state'] = 'held'
elif request['operator_id'] == 'wrong-boot':
    result['boot_id'] = 'wrong'
# A late result is still owned until actual EOF/reap, with both pipes drained.
print('x' * 100000, file=sys.stderr)
if request['operator_id'] == 'malformed-utf8':
    sys.stdout.buffer.write(b'\xff\xfe\x80')
    sys.stdout.buffer.flush()
time.sleep(.05)
(root / ('STATUS.json' if request['operator_id'] == 'pending' else 'RESULT.json')).write_text(json.dumps(result))
print(json.dumps(result))
'''


def create_profile(root, operator='neutral-operator'):
    provider = root / 'quest_shell_recenter.py'
    provider.write_text(PEER)
    request = {'schema':recenter.REQUEST_SCHEMA,'request_id':'a'*32,'nonce':'b'*32,
               'adb':str(root/'adb.exe'),'canonical_serial':'neutral-headset','selector':'neutral-headset',
               'boot_id':'11111111-1111-4111-8111-111111111111','operator_id':operator,
               'artifact':{'path':str(root/'adapter.dex.jar'),'sha256':'c'*64,'bytes':12},
               'source':{'revision':'d'*40,'tree':'e'*40,'source_id':'f'*64},
               'firmware':{'fingerprint':'neutral/fingerprint','vrshell_sha256':'1'*64,'framework_sha256':'2'*64},
               'output_dir':str(root/'provider-output')}
    profile = {'$schema':recenter.PROFILE_SCHEMA,
               'provider':{'path':str(provider),'sha256':recenter.digest(provider.read_bytes())},
               'request':request}
    path = root/'profile.json'
    path.write_text(json.dumps(profile))
    return path, profile


class RecenterCallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_real_child_late_callback_and_replay_remain_separate_from_effect(self):
        path, profile = create_profile(self.root)
        report = recenter.execute(path, 'recenter')
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['callback']['state'], 'success')
        self.assertEqual(report['effect']['state'], 'unverified')
        self.assertTrue(report['original']['retired'])
        self.assertEqual(report['provider_exit_code'], 0)
        duplicate = recenter.execute(path, 'recenter')
        reconciled = recenter.execute(path, 'reconcile')
        for row in (duplicate, reconciled):
            self.assertTrue(row['duplicate_suppressed'])
            self.assertEqual(row['provider_result'], report['provider_result'])
        self.assertIsNone(duplicate['provider_exit_code'])
        self.assertEqual(reconciled['provider_exit_code'], 0)
        self.assertEqual((Path(profile['request']['output_dir'])/'calls').read_text(), 'recenter')

    def test_pending_original_never_retriggers_and_late_result_reconciles(self):
        path, profile = create_profile(self.root, 'pending')
        report = recenter.execute(path, 'recenter')
        self.assertEqual(report['status'], 'warn')
        self.assertFalse(report['original']['retired'])
        result = deepcopy(report['provider_result'])
        result['callback'] = {'state':'success'}
        result['original'] = {'state':'retired','retired':True}
        result['cleanup'] = {'state':'complete'}
        (Path(profile['request']['output_dir'])/'RESULT.json').write_text(json.dumps(result))
        self.assertEqual(recenter.execute(path, 'reconcile')['status'], 'pass')
        self.assertTrue(recenter.execute(path, 'recenter')['duplicate_suppressed'])

    def test_binary_observer_keeps_malformed_utf8_and_reaps_original(self):
        path, _ = create_profile(self.root, 'malformed-utf8')
        report = recenter.execute(path, 'recenter')
        self.assertEqual(report['status'], 'pass')
        observation = report['provider_observation']
        self.assertTrue(observation['observation_complete'])
        self.assertTrue(observation['process_reaped'])
        self.assertTrue(observation['streams']['stdout']['eof'])
        self.assertTrue(observation['streams']['stderr']['eof'])
        raw = Path(observation['streams']['stdout']['descriptor']['path']).read_bytes()
        self.assertIn(b'\xff\xfe\x80', raw)
        self.assertGreater(observation['streams']['stderr']['retained_bytes'], 100000)

    def test_concurrent_callers_share_one_durable_dispatch(self):
        path, _ = create_profile(self.root)
        children = []
        for index in range(2):
            out = self.root/f'concurrent-{index}.json'
            children.append((out, subprocess.Popen([sys.executable,'tools/hostessctl/hostessctl.py',
                'companion-session','shell-recenter','--profile',str(path),'--mode','recenter','--out',str(out)],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE)))
        reports = []
        for out, child in children:
            stdout, stderr = child.communicate()
            self.assertEqual(child.returncode, 0, stderr)
            reports.append(json.loads(out.read_text()))
        self.assertEqual(sum(not report['duplicate_suppressed'] for report in reports), 1)
        self.assertEqual(sum(report['provider_exit_code'] is not None for report in reports), 1)
        self.assertEqual(recenter.execute(path,'reconcile')['callback']['state'], 'success')

    def test_intent_flush_failure_never_launches_or_replays(self):
        path, profile = create_profile(self.root)
        with patch.object(recenter.os, 'fsync', side_effect=OSError('journal flush failed')):
            with self.assertRaisesRegex(OSError, 'journal flush failed'):
                recenter.execute(path, 'recenter')
        self.assertFalse(Path(profile['request']['output_dir']).exists())
        report = recenter.execute(path, 'recenter')
        self.assertTrue(report['duplicate_suppressed'])
        self.assertIsNone(report['provider_exit_code'])
        self.assertEqual(report['dispatch']['state'], 'unknown')
        self.assertFalse(report['original']['retired'])

    def test_errors_and_unsupported_privilege_preserve_original_result(self):
        for name in ('late-error','unavailable','exit-without-result','wrong-boot'):
            with self.subTest(name=name):
                root = self.root/name
                root.mkdir()
                path, _ = create_profile(root, name)
                report = recenter.execute(path, 'recenter')
                self.assertEqual(report['status'], 'fail')
                if name == 'late-error':
                    self.assertEqual(report['callback']['error'], {'code':7,'message':'original error'})
                elif name in ('exit-without-result','wrong-boot'):
                    self.assertEqual(report['dispatch']['state'], 'unknown')
                    self.assertFalse(report['original']['retired'])
                self.assertTrue(recenter.execute(path, 'recenter')['duplicate_suppressed'])

    def test_failed_readiness_and_observer_errors_have_projection_parity(self):
        for operator in ('unavailable', 'exit-without-result'):
            with self.subTest(operator=operator):
                root = self.root/operator
                root.mkdir()
                profile, _ = create_profile(root, operator)
                report = recenter.execute(profile, 'readiness')
                path = root/'report.json'
                path.write_text(json.dumps(report))
                projection = build_companion_report_projection(argparse.Namespace(shell_recenter=[str(path)]), clock_func=utc_now)
                rows = {row['row_id']:row for row in projection['rows']}
                self.assertEqual(rows['shell_recenter.action']['status'], 'fail')
                self.assertEqual(rows['shell_recenter.action']['details']['errors'], report['errors'])
                self.assertEqual(rows['shell_recenter.availability']['status'], 'fail' if operator == 'unavailable' else 'warn')
                self.assertEqual(rows['shell_recenter.effect']['status'], 'warn')

    def test_hash_change_and_output_reuse_fail_before_dispatch(self):
        path, profile = create_profile(self.root)
        provider = Path(profile['provider']['path'])
        provider.write_text(PEER + '\n# change\n')
        with self.assertRaisesRegex(ValueError, 'SHA-256 changed'):
            recenter.execute(path, 'recenter')
        self.assertFalse(Path(profile['request']['output_dir']).exists())
        provider.write_text(PEER)
        recenter.execute(path, 'readiness')
        with self.assertRaisesRegex(ValueError, 'readiness request cannot become'):
            recenter.execute(path, 'recenter')
        profile['request']['nonce'] = '3'*32
        path.write_text(json.dumps(profile))
        with self.assertRaisesRegex(ValueError, 'different exact request'):
            recenter.execute(path, 'readiness')

    def test_cli_catalog_and_report_projection_use_same_evidence(self):
        path, _ = create_profile(self.root)
        out = self.root/'hostess.json'
        child = subprocess.run([sys.executable,'tools/hostessctl/hostessctl.py','companion-session',
                                'shell-recenter','--profile',str(path),'--mode','recenter','--out',str(out)],
                               capture_output=True,text=True,check=False)
        self.assertEqual(child.returncode, 0, child.stderr)
        report = json.loads(out.read_text())
        projection = build_companion_report_projection(argparse.Namespace(shell_recenter=[str(out)]),clock_func=utc_now)
        rows = {row['row_id']:row for row in projection['rows']}
        self.assertEqual(rows['shell_recenter.callback']['status'], 'pass')
        self.assertEqual(rows['shell_recenter.effect']['status'], 'warn')
        self.assertEqual(rows['shell_recenter.effect']['evidence'], 'unverified')
        self.assertTrue(recenter.valid_report(report))
        report['callback']['state'] = 'error'
        out.write_text(json.dumps(report))
        invalid = build_companion_report_projection(argparse.Namespace(shell_recenter=[str(out)]),clock_func=utc_now)
        self.assertEqual(invalid['status'], 'fail')
        catalog = build_companion_catalog_report(argparse.Namespace(),clock_ms_func=lambda:1)
        self.assertEqual(catalog['developer_actions'][0]['action_id'], 'shell_recenter')
        self.assertFalse(catalog['developer_actions'][0]['ordinary_apk_supported'])

    @unittest.skipUnless(os.environ.get('QUEST_SHELL_RECENTER_PROVIDER'), 'explicit external Quest provider pin required')
    def test_external_production_quest_passive_reconciliation(self):
        # Execute the actual Quest producer/validator and actual Hostess caller.
        # Only passive reconciliation is permitted: nonexistent ADB/artifact
        # paths make an accidental live mode fail, rather than reach a device.
        provider = Path(os.environ['QUEST_SHELL_RECENTER_PROVIDER']).resolve()
        pin = json.loads((Path(__file__).resolve().parents[1]/'fixtures/shell-recenter/provider-source.json').read_text())
        self.assertEqual(recenter.digest(provider.read_bytes()), pin['provider_sha256'])
        spec = importlib.util.spec_from_file_location('quest_recenter_contract', provider)
        owner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(owner)
        profile_path, profile = create_profile(self.root)
        profile['provider'] = {'path':str(provider),'sha256':recenter.digest(provider.read_bytes())}
        request = owner.validate(profile['request'])
        request['source'] = {'revision':pin['revision'],'tree':pin['tree'],'source_id':pin['module_source_id']}
        result = owner.initial(request)
        output = Path(request['output_dir'])
        output.mkdir()
        owner.publish(output/'STATUS.json', result)
        raw = json.dumps(profile).encode()
        profile_path.write_bytes(raw)
        intent = {'$schema':recenter.INTENT_SCHEMA,'action':recenter.ACTION,
                  'profile_sha256':recenter.digest(raw),'request_sha256':recenter.digest(recenter.canonical(request)),
                  'provider':profile['provider'],'request_id':request['request_id'],'nonce':request['nonce'],'initial_mode':'recenter'}
        recenter.write_new(output.with_name(output.name+'.hostess-intent.json'),recenter.canonical(intent))
        report = recenter.execute(profile_path, 'reconcile')
        self.assertEqual(report['provider_result'], result)
        self.assertEqual(report['dispatch']['state'], 'not_sent')
        self.assertFalse(report['original']['retired'])
        self.assertEqual(report['effect']['state'], 'unverified')
        self.assertTrue(report['duplicate_suppressed'])
        self.assertFalse(Path(request['adb']).exists())
        self.assertFalse(Path(request['artifact']['path']).exists())


if __name__ == '__main__':
    unittest.main()
