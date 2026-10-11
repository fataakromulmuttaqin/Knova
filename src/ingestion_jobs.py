"""Durable ingestion queue for a single-host deployment; one worker across processes."""
import json
import logging
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

if os.name == "nt":
    import msvcrt

    def _flock(lock, blocking=True):
        # msvcrt.LK_LOCK gives up after ~10s, so retry to match fcntl semantics.
        while True:
            try:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)
                return
            except OSError as exc:
                if blocking:
                    time.sleep(0.2)
                    continue
                raise BlockingIOError(*exc.args) from exc
else:
    import fcntl

    def _flock(lock, blocking=True):
        fcntl.flock(lock, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))

log = logging.getLogger(__name__)

_REPLACE_ATTEMPTS = 10
_REPLACE_DELAY_SECONDS = 0.05
_READ_ATTEMPTS = 3
_READ_DELAY_SECONDS = 0.02


def _replace_with_retry(source: Path, target: Path) -> None:
    """Move source onto target, tolerating Windows readers that block the rename.

    Windows refuses os.replace while another handle holds the target open, and the
    API polls these status files while the worker writes them. Retry briefly, then
    write through the existing file: Windows permits that shared write.
    """
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            source.replace(target)
            return
        except PermissionError:
            if attempt == _REPLACE_ATTEMPTS - 1:
                break
            time.sleep(_REPLACE_DELAY_SECONDS)
    with target.open('w') as handle:
        handle.write(source.read_text())
        handle.flush()
        os.fsync(handle.fileno())
    source.unlink(missing_ok=True)


def _read_json_with_retry(path: Path):
    """Read a status file, retrying briefly while a writer replaces it."""
    for attempt in range(_READ_ATTEMPTS):
        try:
            return json.loads(path.read_text())
        except ValueError:
            if attempt == _READ_ATTEMPTS - 1:
                raise
            time.sleep(_READ_DELAY_SECONDS)


class IngestionJobs:
    def __init__(self, root, process):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.process = process
        self._started = False
        self._stop = threading.Event()
        self._start_lock = threading.Lock()

    def _write(self, directory, job):
        temporary = directory / (uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(job))
        os.chmod(temporary, 0o600)
        _replace_with_retry(temporary, directory / 'status.json')

    def get(self, job_id, user_id):
        if not str(job_id).isalnum():
            raise KeyError(job_id)
        try:
            job = _read_json_with_retry(self.root / job_id / 'status.json')
        except (OSError, ValueError):
            raise KeyError(job_id)
        if job['user_id'] != user_id:
            raise KeyError(job_id)
        return {key: value for key, value in job.items() if key not in {'user_id', 'inputs'}}

    def active(self, user_id):
        jobs = []
        for path in self.root.glob('*/status.json'):
            job = _read_json_with_retry(path)
            if job['user_id'] == user_id and job['status'] in {'queued', 'running'}:
                jobs.append(self.get(job['job_id'], user_id))
        return jobs

    def submit(self, user_id, files=(), kind='upload', payload=None):
        # Serialize admission across threads/processes; bound storage and CPU backlog.
        with (self.root / 'admission.lock').open('a') as lock:
            _flock(lock)
            records = [_read_json_with_retry(path) for path in self.root.glob('*/status.json')]
            pending = [job for job in records if job['status'] in {'queued', 'running'}]
            if any(job['user_id'] == user_id for job in pending):
                raise ValueError('You already have documents processing. Wait for them to finish before adding more.')
            if len(pending) >= 10:
                raise ValueError('The indexing queue is full. Please try again shortly.')
            job_id = uuid.uuid4().hex
            directory = self.root / job_id
            directory.mkdir(mode=0o700)
            inputs = []
            try:
                for index, (name, content_type, content) in enumerate(files):
                    path = directory / str(index)
                    path.write_bytes(content)
                    os.chmod(path, 0o600)
                    inputs.append({'name': name, 'content_type': content_type, 'file': str(index)})
                job = {'job_id': job_id, 'user_id': user_id, 'kind': kind, 'payload': payload,
                       'inputs': inputs, 'name': ('Google Drive documents' if kind == 'drive' else inputs[0]['name'] if len(inputs) == 1 else f'{len(inputs)} documents'),
                       'size': sum(len(item[2]) for item in files), 'status': 'queued', 'phase': 'Waiting to index',
                       'percent': 0, 'created_at': time.time(), 'updated_at': time.time()}
                self._write(directory, job)
            except Exception:
                shutil.rmtree(directory)
                raise
        self.start()
        return self.get(job_id, user_id)

    def start(self):
        with self._start_lock:
            if self._started:
                return
            self._started = True
            threading.Thread(target=self._run, daemon=True, name='ingestion-worker').start()

    def stop(self):
        self._stop.set()

    def _run(self):
        # Held for the worker lifetime. Another process can take over after a crash.
        with (self.root / 'worker.lock').open('a') as lock:
            while not self._stop.is_set():
                try:
                    _flock(lock, blocking=False)
                    break
                except BlockingIOError:
                    self._stop.wait(1)
            if self._stop.is_set():
                return
            for path in self.root.glob('*/status.json'):
                job = _read_json_with_retry(path)
                if job['status'] == 'running':
                    job.update(status='queued', phase='Resuming indexing', percent=0)
                    self._write(path.parent, job)
            while not self._stop.is_set():
                paths = sorted(self.root.glob('*/status.json'), key=lambda path: path.parent.name)
                jobs = [(path, _read_json_with_retry(path)) for path in paths]
                queued = sorted([(path, job) for path, job in jobs if job['status'] == 'queued'], key=lambda item: item[1]['created_at'])
                for path, job in queued:
                    directory = path.parent
                    last_reported = {'phase': None, 'percent': None}

                    def progress(phase, percent):
                        value = int(percent)
                        # Skip duplicate writes: every write contends with the API
                        # polling this same file, which is what breaks writes on Windows.
                        if phase == last_reported['phase'] and value == last_reported['percent']:
                            return
                        last_reported.update(phase=phase, percent=value)
                        job.update(status='running', phase=phase, percent=value, updated_at=time.time())
                        self._write(directory, job)
                    try:
                        progress('Reading documents', 2)
                        result = self.process(job, directory, progress)
                        failed = result.get('ok') is False or result.get('source_count', result.get('count', 1)) == 0
                        job.update(status='failed' if failed else 'completed', percent=100, result=result,
                                   phase='No indexable text' if failed else 'Ready to ask questions')
                    except Exception:
                        log.exception('Ingestion job %s failed', job['job_id'])
                        job.update(status='failed', error='Document processing failed. Please try again or contact support with job ' + job['job_id'], phase='Indexing failed')
                    finally:
                        job['updated_at'] = time.time()
                        self._write(directory, job)
                        for item in job['inputs']:
                            (directory / item['file']).unlink(missing_ok=True)
                    log.info('Ingestion job %s %s in %.1fs', job['job_id'], job['status'], time.time() - job['created_at'])
                for path, job in jobs:
                    if job['status'] in {'completed', 'failed'}:
                        for item in job['inputs']:
                            (path.parent / item['file']).unlink(missing_ok=True)
                        if time.time() - job['updated_at'] > 7 * 86400:
                            shutil.rmtree(path.parent, ignore_errors=True)
                self._stop.wait(1)
