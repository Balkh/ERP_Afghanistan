"""Replay bookmarks — save and restore replay positions."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplayBookmark


class ReplayBookmarks:
    def __init__(self, max_bookmarks: int = 100):
        self._bookmarks: Dict[str, ReplayBookmark] = {}
        self._bookmark_list: deque = deque(maxlen=max_bookmarks)

    def add_bookmark(self, bookmark_id: str, tick: int, label: str,
                     description: str = "",
                     snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        bookmark = ReplayBookmark(
            bookmark_id=bookmark_id, tick=tick, label=label,
            description=description, snapshot_id=snapshot_id,
        )
        self._bookmarks[bookmark_id] = bookmark
        self._bookmark_list.append(bookmark_id)
        return {'bookmark_id': bookmark_id, 'tick': tick,
                'label': label, 'snapshot_id': snapshot_id}

    def get_bookmark(self, bookmark_id: str) -> Optional[Dict[str, Any]]:
        b = self._bookmarks.get(bookmark_id)
        if b is None:
            return None
        return {'bookmark_id': b.bookmark_id, 'tick': b.tick,
                'label': b.label, 'description': b.description,
                'snapshot_id': b.snapshot_id}

    def list_bookmarks(self) -> List[Dict[str, Any]]:
        return [{'bookmark_id': b.bookmark_id, 'tick': b.tick,
                 'label': b.label, 'description': b.description}
                for b in self._bookmarks.values()]

    def remove_bookmark(self, bookmark_id: str) -> bool:
        if bookmark_id in self._bookmarks:
            del self._bookmarks[bookmark_id]
            return True
        return False

    def clear(self):
        self._bookmarks.clear()
        self._bookmark_list.clear()
