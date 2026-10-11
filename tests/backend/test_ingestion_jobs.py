import json
import threading
import time
from pathlib import Path

import pytest

from src.ingestion_jobs import IngestionJobs, _read_json_with_retry, _replace_with_retry


def wait_until(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError('Job did not finish')


def test_queue_returns_before_processing_and_is_user_scoped(tmp_path):
    started, release = threading.Event(), threading.Event()
    def process(job, directory, progress):
        assert (directory / '0').read_bytes() == b'document'
        progress('Creating searchable embeddings', 45)
        started.set()
        release.wait(3)
        return {'ok': True, 'source_count': 1}
    queue = IngestionJobs(tmp_path, process)
    try:
        job = queue.submit('alice', [('a.txt', 'text/plain', b'document')])
        assert started.wait(2)
        assert queue.get(job['job_id'], 'alice')['percent'] == 45
        with pytest.raises(KeyError):
            queue.get(job['job_id'], 'bob')
        assert queue.active('bob') == []
        with pytest.raises(ValueError):
            queue.submit('alice', [('b.txt', 'text/plain', b'new')])
        release.set()
        wait_until(lambda: queue.get(job['job_id'], 'alice')['status'] == 'completed')
        wait_until(lambda: not (tmp_path / job['job_id'] / '0').exists())
    finally:
        release.set()
        queue.stop()


def test_restart_resumes_interrupted_job(tmp_path):
    directory = tmp_path / 'abcdef'
    directory.mkdir()
    (directory / '0').write_bytes(b'persisted')
    (directory / 'status.json').write_text(json.dumps({
        'job_id': 'abcdef', 'user_id': 'alice', 'status': 'running',
        'created_at': time.time(), 'updated_at': time.time(), 'inputs': [{'file': '0'}],
    }))
    queue = IngestionJobs(tmp_path, lambda job, directory, progress: {'ok': True, 'source_count': 1})
    try:
        queue.start()
        wait_until(lambda: queue.get('abcdef', 'alice')['status'] == 'completed')
    finally:
        queue.stop()


def test_failed_job_has_safe_error_and_removes_upload(tmp_path):
    def process(*args):
        raise RuntimeError('private internal details')
    queue = IngestionJobs(tmp_path, process)
    try:
        job = queue.submit('alice', [('a.txt', 'text/plain', b'data')])
        wait_until(lambda: queue.get(job['job_id'], 'alice')['status'] == 'failed')
        assert 'private internal details' not in queue.get(job['job_id'], 'alice')['error']
        wait_until(lambda: not (tmp_path / job['job_id'] / '0').exists())
    finally:
        queue.stop()


def test_status_write_survives_a_reader_holding_the_file_open(tmp_path):
    """Windows refuses os.replace while a reader holds the target open.

    Status is polled through the API while the worker writes it, so a plain replace
    made large uploads fail with PermissionError [WinError 5].
    """
    queue = IngestionJobs(tmp_path, lambda *args: {'ok': True, 'source_count': 1})
    directory = tmp_path / 'busy'
    directory.mkdir()
    queue._write(directory, {'job_id': 'busy', 'user_id': 'alice', 'status': 'queued', 'percent': 0})

    with (directory / 'status.json').open('r', encoding='utf-8') as holder:
        assert holder.read()
        queue._write(directory, {'job_id': 'busy', 'user_id': 'alice', 'status': 'running', 'percent': 42})

    assert queue.get('busy', 'alice')['percent'] == 42


def test_status_reader_retries_a_partially_written_file(tmp_path):
    target = tmp_path / 'status.json'
    target.write_text('{"job_id": "x", ', encoding='utf-8')

    def repair():
        time.sleep(.03)
        target.write_text('{"job_id": "x", "status": "queued"}', encoding='utf-8')

    thread = threading.Thread(target=repair)
    thread.start()
    try:
        assert _read_json_with_retry(target)['status'] == 'queued'
    finally:
        thread.join()


def test_replace_helper_writes_through_when_renaming_is_denied(tmp_path, monkeypatch):
    target = tmp_path / 'status.json'
    target.write_text('{"percent": 1}', encoding='utf-8')
    source = tmp_path / 'next.tmp'
    source.write_text('{"percent": 2}', encoding='utf-8')

    def denied(self, other):
        raise PermissionError(5, 'Access is denied')

    monkeypatch.setattr(Path, 'replace', denied)
    monkeypatch.setattr('src.ingestion_jobs._REPLACE_ATTEMPTS', 2)
    monkeypatch.setattr('src.ingestion_jobs._REPLACE_DELAY_SECONDS', 0)

    _replace_with_retry(source, target)

    assert json.loads(target.read_text(encoding='utf-8'))['percent'] == 2
    assert not source.exists()
