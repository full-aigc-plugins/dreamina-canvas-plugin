"""ResourceUploader 与真实适配器返回类型的组合回归。"""
import tempfile
import unittest
from pathlib import Path
from test_visual_loop_runtime import ScriptedRunner, envelope, failure, SESSION, RESOURCE
from target_store import TargetStore, ResourceUploader

class UploaderCompositionTests(unittest.TestCase):
    def test_command_result_success_conflict_and_restart(self):
        for results in ([envelope({'resourceId': RESOURCE})],
                        [failure(2, {'code': 'cli.resource_already_exists'}, 'resume'),
                         envelope({'resourceId': RESOURCE})],
                        [failure(20, {'code': 'transport'}, 'resume'),
                         envelope({'resourceId': RESOURCE})]):
            with self.subTest(results=results), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                store = TargetStore(root=root / '.loop', approved_root=root, session_id=SESSION)
                runner = ScriptedRunner(results)
                uploader = ResourceUploader(runner=runner, store=store, project_id=SESSION)
                kwargs = dict(path=root / 'image.png', resource_id=RESOURCE, import_kind='local_upload')
                self.assertEqual(uploader.upload(**kwargs).resource_id, RESOURCE)
                self.assertEqual(uploader.upload(**kwargs).resource_id, RESOURCE)
                self.assertEqual(sum('upload' in argv for argv in runner.argvs), 1)

    def test_success_without_valid_resource_does_not_complete_intent(self):
        from target_store import TargetError
        for data in ({}, {'resourceId': 'invalid'}):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                store = TargetStore(root=root / '.loop', approved_root=root, session_id=SESSION)
                runner = ScriptedRunner([envelope(data)])
                uploader = ResourceUploader(runner=runner, store=store, project_id=SESSION)
                with self.assertRaises(TargetError):
                    uploader.upload(path=root / 'image.png', resource_id=RESOURCE, import_kind='local_upload')
                self.assertIsNone(store.loop_state.pending_intent(kind='resource_upload', submit_id=RESOURCE)['result'])

    def test_transport_exception_restart_only_queries_original_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = TargetStore(root=root / '.loop', approved_root=root, session_id=SESSION)
            def timeout(argv):
                raise TimeoutError('connection lost')
            uploader = ResourceUploader(runner=timeout, store=store, project_id=SESSION)
            kwargs = dict(path=root / 'image.png', resource_id=RESOURCE, import_kind='local_upload')
            with self.assertRaises(TimeoutError):
                uploader.upload(**kwargs)
            runner = ScriptedRunner([envelope({'resourceId': RESOURCE})])
            resumed = ResourceUploader(runner=runner, store=store, project_id=SESSION)
            self.assertEqual(resumed.upload(**kwargs).resource_id, RESOURCE)
            self.assertTrue(all('upload' not in argv for argv in runner.argvs))
