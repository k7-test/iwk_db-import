from __future__ import annotations

from types import SimpleNamespace

from src.services.fk_propagation import build_fk_propagation_maps


def test_build_fk_maps_sequence_detection_variants():
    """build_fk_propagation_maps における parent_pk_column 推定分岐を網羅。

    ケース:
      1) sequences に table.col 形式キーが存在 -> その col を parent_pk_column に採用
      2) sequences の値が dict で column 指定 -> その column を採用
    2 エントリの fk_propagations list を与え、両方のコードパスをヒットさせる。
    """
    config = SimpleNamespace(
        fk_propagations=[
            {"parent": "p1.identifier", "child": "c1.fk1"},
            {"parent": "p2.identifier", "child": "c2.fk2"},
        ],
        sequences={
            # table.col 形式 (p1.id) -> case 1
            'p1.id': 'p1_id_seq',
            # 値 dict 形式 -> case 2
            'legacy_seq': {'column': 'custom_pk'},
        },
        pk_columns=None,
    )

    maps = build_fk_propagation_maps(config)
    # parent_table 順 (呼び出し順) に対応
    assert len(maps) == 2
    # p1 は table.col キーから id 推定
    assert any(m.parent_table == 'p1' and m.parent_pk_column == 'id' for m in maps)
    # p2 は dict value の column -> custom_pk
    assert any(m.parent_table == 'p2' and m.parent_pk_column == 'custom_pk' for m in maps)
