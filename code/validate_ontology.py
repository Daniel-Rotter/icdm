"""
validate_ontology.py

Validates the ICDM ontology against the SHACL shapes in shapes.ttl, using
pySHACL. Run generate_test_data.py first to produce the two supplementary
data files this script loads alongside the main ontology.

Usage:
    python generate_test_data.py
    python validate_ontology.py

This script does *not* resolve the ontology's owl:imports (SAREF core,
SAREF4BLDG, SAREF4ENER, SAREF4GRID) over the network. The five shapes here
only need the asserted data triples, not the imported TBox axioms, so this
keeps validation fast, offline, and reproducible. If a shape you add later
genuinely needs entailment from the imports (e.g. reasoning over class
hierarchies), load the four SAREF files locally first and pass them via
`ont_graph=` to pyshacl.validate(), and/or set `inference="rdfs"` or
`"owlrl"`.
"""

import sys
from rdflib import Graph
from pyshacl import validate

DATA_FILES = [
    "master-thesis\\fhj-script-v4.2b\\docs\\data_models\\icdm_turtle",
    "master-thesis\\fhj-script-v4.2b\\docs\\code\\generated_files\\synthetic_price_timeseries.ttl",
    "master-thesis\\fhj-script-v4.2b\\docs\\code\\generated_files\\test_fixtures.ttl",
]
SHAPES_FILE = "master-thesis\\fhj-script-v4.2b\\docs\\code\\shapes.ttl"

def load_data_graph(paths: list[str]) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path, format="turtle")
    return g


def summarise_violations(results_graph: Graph) -> None:
    """Print one line per validation result: which shape, which individual,
    and the message, easier to scan than the raw text report for a large
    number of results (e.g. 96 price points)."""
    query = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    SELECT ?focusNode ?resultMessage ?sourceShape
    WHERE {
        ?result a sh:ValidationResult ;
                sh:focusNode ?focusNode ;
                sh:resultMessage ?resultMessage ;
                sh:sourceShape ?sourceShape .
    }
    ORDER BY ?sourceShape ?focusNode
    """
    rows = list(results_graph.query(query))
    if not rows:
        print("No violations.")
        return
    current_shape = None
    for focus_node, message, source_shape in rows:
        shape_name = str(source_shape).split("#")[-1]
        if shape_name != current_shape:
            print(f"\n--- {shape_name} ---")
            current_shape = shape_name
        node_name = str(focus_node).split("#")[-1]
        print(f"  {node_name}: {message}")


def main() -> int:
    print("Loading data graph:", ", ".join(DATA_FILES))
    data_graph = load_data_graph(DATA_FILES)
    print(f"  {len(data_graph)} triples total\n")

    print("Loading shapes graph:", SHAPES_FILE)
    shapes_graph = Graph()
    shapes_graph.parse(SHAPES_FILE, format="turtle")
    print(f"  {len(shapes_graph)} triples\n")

    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference=None,       # no OWL/RDFS entailment: shapes only need asserted data
        abort_on_first=False, # collect every violation, not just the first
        allow_infos=True,
        meta_shacl=False,
        advanced=True,        # required for sh:sparql (SPARQL-based constraints)
        js=False,
    )

    print("=" * 60)
    print(f"CONFORMS: {conforms}")
    print("=" * 60)

    summarise_violations(results_graph)

    print("\n" + "=" * 60)
    print("Full pySHACL text report (for reference):")
    print("=" * 60)
    print(results_text)

    return 0 if conforms else 1


if __name__ == "__main__":
    sys.exit(main())
