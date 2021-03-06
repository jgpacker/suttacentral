from datetime import datetime
from threading import Thread
from plumbum import local

import sc
from sc.scm import data_scm
from sc.util import filelock

lock_path = sc.tmp_dir / 'update_data.lock'

def last_update():
    """Return the last time an update was run or None for never."""
    try:
        mtime = lock_path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(mtime)

def update(bg=False):
    """Update the data directory.

    If bg is True, then update in the background."""
    def _update():
        with local.cwd(sc.data_dir):
            local['git']['pull']()
    block = not bg
    with filelock(lock_path, block=block) as acquired:
        if acquired:
            if bg:
                thread = Thread(target=_update)
                thread.start()
            else:
                _update()
