"""Tests for DrugClass monitoring edge propagation."""

from unittest.mock import patch

from open_medicine.graphrag.ingestion.loader_v2 import (
    propagate_monitoring_to_classes,
)


class TestMonitoringPropagation:
    def test_propagate_monitoring_creates_class_edges(self):
        """MONITORED_BY edges on member drugs should propagate to parent DrugClass."""
        from open_medicine.graphrag.ingestion.linker_v2 import LinkedEntity

        # Simulate seen entities
        spiro = LinkedEntity(
            canonical_name="Spironolactone",
            entity_type="drug",
            node_label="Drug",
            node_id="rxnorm:9997",
        )
        mra = LinkedEntity(
            canonical_name="MRA",
            entity_type="drug_class",
            node_label="DrugClass",
            node_id="atc:C03DA",
        )
        seen = {spiro.node_id: spiro, mra.node_id: mra}

        # Simulate existing queries with a MONITORED_BY edge for spiro
        queries = [
            (
                "MATCH (d:Drug {id: $did}), (l:Lab {id: $lid}) "
                "MERGE (d)-[r:MONITORED_BY]->(l) "
                "ON CREATE SET r.frequency = $freq, r.threshold_alert = $alert, "
                "r.threshold_stop = $stop, r.conditions_json = $conds",
                {
                    "did": "rxnorm:9997",
                    "lid": "loinc:2823-3",
                    "freq": "within 1 week",
                    "alert": "K > 5.0",
                    "stop": "K > 5.5",
                    "conds": None,
                },
            ),
        ]

        with patch(
            "open_medicine.graphrag.ingestion.loader_v2.get_drug_class_members"
        ) as mock_members:
            mock_members.return_value = ["Spironolactone", "Eplerenone"]
            with patch(
                "open_medicine.graphrag.ingestion.loader_v2.link_entity"
            ) as mock_link:
                mock_link.return_value = spiro
                result = propagate_monitoring_to_classes(queries, seen)

        assert len(result) >= 1
        # Check that a DrugClass MONITORED_BY edge was created
        cypher, params = result[0]
        assert "DrugClass" in cypher
        assert "MONITORED_BY" in cypher
        assert params["did"] == "atc:C03DA"
        assert params["lid"] == "loinc:2823-3"
        assert "propagated" in cypher

    def test_no_propagation_without_monitoring_edges(self):
        """If no member drugs have MONITORED_BY edges, nothing propagates."""
        from open_medicine.graphrag.ingestion.linker_v2 import LinkedEntity

        mra = LinkedEntity(
            canonical_name="MRA",
            entity_type="drug_class",
            node_label="DrugClass",
            node_id="atc:C03DA",
        )
        seen = {mra.node_id: mra}

        # No MONITORED_BY queries
        queries = [
            (
                "MATCH (d:Drug {id: $did})-[r:INDICATED_FOR]->(dis:Disease {id: $dis_id})",
                {"did": "rxnorm:9997", "dis_id": "snomed:42343007"},
            ),
        ]

        with patch(
            "open_medicine.graphrag.ingestion.loader_v2.get_drug_class_members"
        ) as mock_members:
            mock_members.return_value = ["Spironolactone"]
            with patch(
                "open_medicine.graphrag.ingestion.loader_v2.link_entity"
            ) as mock_link:
                mock_link.return_value = None
                result = propagate_monitoring_to_classes(queries, seen)

        assert len(result) == 0

    def test_deduplicates_class_lab_pairs(self):
        """Same lab monitored by multiple members should create only one class edge."""
        from open_medicine.graphrag.ingestion.linker_v2 import LinkedEntity

        spiro = LinkedEntity(
            canonical_name="Spironolactone",
            entity_type="drug",
            node_label="Drug",
            node_id="rxnorm:9997",
        )
        epler = LinkedEntity(
            canonical_name="Eplerenone",
            entity_type="drug",
            node_label="Drug",
            node_id="rxnorm:298869",
        )
        mra = LinkedEntity(
            canonical_name="MRA",
            entity_type="drug_class",
            node_label="DrugClass",
            node_id="atc:C03DA",
        )
        seen = {spiro.node_id: spiro, epler.node_id: epler, mra.node_id: mra}

        # Both drugs monitor same lab
        queries = [
            (
                "... MONITORED_BY ...",
                {
                    "did": "rxnorm:9997",
                    "lid": "loinc:2823-3",
                    "freq": "weekly",
                    "alert": None,
                    "stop": None,
                    "conds": None,
                },
            ),
            (
                "... MONITORED_BY ...",
                {
                    "did": "rxnorm:298869",
                    "lid": "loinc:2823-3",
                    "freq": "weekly",
                    "alert": None,
                    "stop": None,
                    "conds": None,
                },
            ),
        ]

        with patch(
            "open_medicine.graphrag.ingestion.loader_v2.get_drug_class_members"
        ) as mock_members:
            mock_members.return_value = ["Spironolactone", "Eplerenone"]
            with patch(
                "open_medicine.graphrag.ingestion.loader_v2.link_entity"
            ) as mock_link:

                def link_side_effect(name, entity_type):
                    if name == "Spironolactone":
                        return spiro
                    if name == "Eplerenone":
                        return epler
                    return None

                mock_link.side_effect = link_side_effect
                result = propagate_monitoring_to_classes(queries, seen)

        # Should only create ONE edge for MRA->Potassium, not two
        assert len(result) == 1
