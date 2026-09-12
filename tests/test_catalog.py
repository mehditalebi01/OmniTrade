from omnitrade.engine.catalog import NODE_CATALOG, NODE_DESCRIPTIONS


def test_catalog_has_exactly_31_owned_node_types():
    assert len(NODE_CATALOG) == 31


def test_every_node_has_a_short_role_description():
    assert NODE_DESCRIPTIONS.keys() == NODE_CATALOG.keys()
    assert all(20 <= len(description) <= 120 for description in NODE_DESCRIPTIONS.values())
    assert {spec.group for spec in NODE_CATALOG.values()} == {
        "control",
        "evidence",
        "normalization",
        "calculation",
        "specialist",
        "research",
        "risk",
        "output",
    }
