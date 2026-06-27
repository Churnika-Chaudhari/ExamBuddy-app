"""Syllabus unit/chapter assignment for extracted topics."""

from __future__ import annotations

SYLLABUS_UNITS: dict[str, list[str]] = {
    "Data Structures": [
        "tree", "graph", "stack", "queue", "linked list", "hashing", "heap", "array", "bst", "avl",
    ],
    "Algorithms": [
        "algorithm", "sorting", "searching", "dijkstra", "dynamic programming", "greedy", "complexity",
    ],
    "Operating Systems": [
        "operating system", "process", "thread", "deadlock", "scheduling", "memory", "paging", "semaphore",
    ],
    "Database Systems": [
        "database", "sql", "normalization", "transaction", "index", "relational", "primary key",
        "foreign key", "dbms", "schema", "keys",
    ],
    "Computer Networks": [
        "network", "tcp", "udp", "ip", "osi", "routing", "protocol", "http", "https", "socket", "dns",
    ],
    "Cloud Computing": ["cloud computing", "virtualization", "saas", "paas", "iaas"],
    "Programming & OOP": [
        "object oriented", "polymorphism", "inheritance", "encapsulation", "class", "java", "python",
    ],
    "Software Engineering": ["software", "sdlc", "agile", "testing", "uml", "requirement"],
    "Theory of Computation": ["automata", "compiler", "grammar", "turing", "finite state"],
}


def assign_syllabus_unit(topic: str) -> str:
    lower = topic.lower()
    for unit, keywords in SYLLABUS_UNITS.items():
        if any(kw in lower for kw in keywords):
            return unit
    return "General"
