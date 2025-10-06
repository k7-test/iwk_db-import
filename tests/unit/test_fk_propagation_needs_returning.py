from __future__ import annotations

from types import SimpleNamespace

from src.services.fk_propagation import needs_returning


def test_needs_returning_dict_true():
    """旧 dict 形式で parent->child 参照があり、child が未処理なら True を返す。"""
    config = SimpleNamespace(
        fk_propagations={
            'parent.id': 'child.parent_id'
        }
    )
    assert needs_returning('parent', config, processed_tables=set()) is True


def test_needs_returning_dict_false_when_child_already_processed():
    """旧 dict 形式で child が processed_tables に含まれていると False。実運用では稀ケースだが分岐網羅。"""
    config = SimpleNamespace(
        fk_propagations={
            'parent.id': 'child.parent_id'
        }
    )
    # child を既に processed と仮定 (カバレッジ目的)
    assert needs_returning('parent', config, processed_tables={'child'}) is False
