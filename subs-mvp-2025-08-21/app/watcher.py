import threading
import time
import asyncio
from kubernetes import client, config, watch

from .config import settings
from .db import upsert_uids_from_cm
from .util import parse_uuid_list_from_clients_json

class CMWatcher:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def start_in_thread(self):
        t = threading.Thread(target=self._run, name="cm-watcher", daemon=True)
        t.start()
        return t

    def _run(self):
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        w = watch.Watch()

        def handle_cm(cm):
            md = cm.metadata
            data = cm.data or {}
            labels = md.labels or {}
            pool = labels.get(settings.POOL_LABEL_KEY)
            if not pool:
                return
            payload = data.get(settings.CM_CLIENTS_KEY)
            if not payload:
                return
            uids = parse_uuid_list_from_clients_json(payload)
            if not uids:
                return
            fut = asyncio.run_coroutine_threadsafe(
                upsert_uids_from_cm(md.name, str(pool), uids),
                self._loop,
            )
            try:
                fut.result(timeout=60)
            except Exception:
                pass

        while not self._stop.is_set():
            try:
                cms = v1.list_namespaced_config_map(
                    namespace=settings.WATCH_NAMESPACE,
                    label_selector=settings.WATCH_LABEL_SELECTOR,
                    _request_timeout=30,
                )
                for cm in cms.items:
                    handle_cm(cm)

                for event in w.stream(
                    v1.list_namespaced_config_map,
                    namespace=settings.WATCH_NAMESPACE,
                    label_selector=settings.WATCH_LABEL_SELECTOR,
                    timeout_seconds=settings.RESCAN_INTERVAL_SEC,
                ):
                    if self._stop.is_set():
                        break
                    obj = event.get("object")
                    et = event.get("type")
                    if et in ("ADDED", "MODIFIED") and obj is not None:
                        handle_cm(obj)
            except Exception:
                time.sleep(5)
