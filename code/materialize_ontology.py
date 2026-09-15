"""
materialize_ontology.py

Jena Fuseki serves whatever triples are actually in its dataset. It does
not run a DL reasoner like HermiT over the data at query time. This means
a class defined via equivalence and nominals, such as
dm:EffectivelyControllable, has *no* asserted members at all until those
memberships are computed and written into the graph as real triples
("materialized"). Querying Fuseki without this step first would silently
return nothing for exactly the queries that matter most.

This script performs that materialization with owlrl's OWL-RL reasoner
(pure Python, no external services), and writes out a single merged Turtle
file ready to load into Fuseki. OWL-RL is a decidable *subset* of OWL DL;
it was verified separately (see the accompanying validation run) to
correctly materialize every axiom actually used in this ontology,
including dm:EffectivelyControllable's conjunction + nominal restrictions,
but it does not implement full DL reasoning (HermiT does, and is what
Protégé itself uses for the logical-consistency check reported in
Section~\\ref{subsec:impl_logical_consistency_validation}). This script's
job is narrower and complementary: make the *results* of that reasoning
queryable, not re-derive them from scratch.

Usage:
    python materialize_ontology.py icdm.ttl [additional.ttl ...] -o materialized.ttl
"""

import argparse
import sys
from rdflib import Graph, Literal
import owlrl


def materialize(input_paths: list[str], output_path: str) -> None:
    g = Graph()
    for path in input_paths:
        g.parse(path, format="turtle")
    before = len(g)
    print(f"Loaded {before} asserted triples from {len(input_paths)} file(s).")

    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    after_reasoning = len(g)
    print(f"Materialized {after_reasoning - before} additional inferred triples "
          f"({after_reasoning} total).")

    # owlrl's OWL-RL implementation has a confirmed bug: some of its datatype
    # entailment rules incorrectly treat a literal value itself as a subject
    # (e.g. asserting "2021-03-15T00:00:00"^^xsd:dateTime rdf:type xsd:dateTime,
    # with the literal as subject). This is invalid RDF. Literals can never
    # be subjects, and rdflib silently tolerates holding such triples in
    # memory, but a strict parser like Jena's correctly refuses to load them.
    # Confirmed by testing: every literal value in this ontology triggers it,
    # not just one. Removed here rather than left for Fuseki to reject.
    invalid = [(s, p, o) for s, p, o in g if isinstance(s, Literal)]
    for triple in invalid:
        g.remove(triple)
    if invalid:
        print(f"Removed {len(invalid)} invalid (literal-subject) triples "
              f"introduced by OWL-RL materialization.")
    after = len(g)

    g.serialize(destination=output_path, format="ttl", encoding="utf-8")
    print(f"Wrote {output_path} ({after} triples), ready to load into Fuseki.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="Turtle files to load and merge")
    parser.add_argument("-o", "--output", default="materialized.ttl")
    args = parser.parse_args()
    materialize(args.inputs, args.output)
    sys.exit(0)
